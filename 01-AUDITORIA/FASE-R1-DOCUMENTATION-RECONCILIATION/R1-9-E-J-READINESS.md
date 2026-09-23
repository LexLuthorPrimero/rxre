# R1-9 — READINESS DE FASE E–J (precondiciones para avanzar)

> **Tarea R-1.9** — FASE R-1 — 2026-09-22 — SOLO DOCUMENTAL
> Evalúa si las fases pendientes E–J están listas para diseñarse con la evidencia actual y qué reclaman las fases
> intermedias (D etapa 3, M) que están antes en prioridad. No autoriza nada: solo readiness.

---

## Regla de orden antes de E–J (según MASTER-PLAN prioridades INMEDIATAS + roadmap)

Precedentes necesarios:
1. **FASE D etapa 3 (contadores)** — requiere traer el mapa de eventos GFX8 (R-0 ya lo aportó) y **nueva
   autorización explícita** para programar; hoy NO autorizada → D-3 sigue BLOQUEADA por autorización (ya NO por mapa).
2. **FASE M** — documento de contadores ya autoresuelto por R-0; queda convertir en «research activo» si se desea.
3. Solo después de aclarar D-3/M se ejecutan los experimentos orientados a E–J.

## Por fase (estado actual de precondiciones)

| Fase | Objetivo | Precondiciones | ¿READY para diseña? | ¿READY para ejecutar? | Gaps bloqueantes |
|---|---|---|---|---|---|
| **E — Real-Game Baseline** | Juego reproducible offline ≥30 s, RX550 explícita, telemetría unificada | Tener benchmark reproducible; telemetría OK (Sistema Lab K futuro); identificador PCI robusto (R1-8 §8) | SÍ (parcial) | **NO** (falta autorización + selección de juego + integración telemetría) | GAP-03, GAP-07 (PCIe), GAP-05 |
| **F — Geometry Investigation** | Candidatos GEO-01..08, mayor valor informativo | Mapa subsistemas (POLARIS12-MAP) ✓ | SÍ | NO | ninguno documental crítico |
| **G — Memory/VRAM/GTT** | Modelo tráfico memoria + contadores/sysfs | Semántica MC **UNRESOLVED** (R1-1) → **BLOQUEANTE** para diseño fino | PARCIAL | NO | GAP-04, GAP-02, GAP-09 (MC semántica) |
| **H — RADV/Workarounds** | Investigar shrink_image_store, wait_for_vm_map etc. | Workarounds GFX8 enumerados (R0-3) ✓ | SÍ | NO | GAP-05 (DCC) |
| **I — PowerPlay/DPM** | pp_power_profile_mode, ppfeaturemask, DPM intermedios | Capability Audit (R1-8 §1, read-only) ✓; política DPM conocida (R0-2) ✓ | SÍ (diseño) | **NO** (writes) | GAP-01 (cap↔SCLK), GAP-10 |
| **J — Priority Matrix** | `EXPERIMENT-PRIORITY-MATRIX.md` | Inputs: R1-7 (gaps), estados R1-6, evidencia R-0, resultados D | SÍ | N/A (documental) | ninguno |

## Observación transversal

Las fases E–J pueden **diseñarse** ya (documental) pero **no ejecutarse** hasta:
1. Autorización explícita (incluida la de ejecutar juegos/benchmarks y escribir sysfs cuando proceda),
2. Framework de Laboratorio K (planificado) o al menos telemetría normalizada,
3. Resolución de los gaps de prioridad ALTA (GAP-01/04/07/08/09) o aceptación explícita del riesgo.

## Confirmación read-only

Evaluación basada solo en documentación; sin ejecuciones.