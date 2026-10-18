# Decisiones Estructurales (§22)

## D1 — Clasificación crítica (ÉTER)
Evento crítico = cumple ≥2 de: resultado hardware (MMIO/PCIe), evidencia no regenerable, prerequisito transformación FUEGO, generado por plano (no AIRE/TIERRA). Implementado en `core/eter.py`: campo `critical`. Write-ahead obligatorio para críticos.

## D2 — Severidad contradicción
Severidad = f(impacto, confianza, alcance). CRITICAL contradice PROVEN; HIGH contradice PARTIAL con evidencia directa; MEDIUM indirecta; LOW débil. Regla en `store.py` sobre `finding_reevaluations`.

## D3 — Autoridad de aceptación
Propietario repositorio (`lucas`) o delegado nombrado por escrito (`audit/AUTHORITY.md`). No constructor ni revisor independiente. Implementado (`core/puerta.py`: `autoridad_nombrada`).

## D4 — Selección backend (ROUTER)
Prioridad: disponibilidad → compatibilidad parámetros → precisión por tipo → coste → fallback. `dispatch.py` `resolve()` implementado; fallback pendiente.

## D5 — Frontera AGUA/TIERRA
TIERRA = evidencia primaria (hashes/claims/contradicciones). AGUA = lecciones derivadas, con `procedencia` a finding. AGUA no crea claims; revalida al recuperar. `core/agua.py` separado.

## D6 — Sync MENTE↔CUERPO↔FUEGO
Directo vía `machine(op=...)`. No bus. Errores como excepciones. Implementado (`invocar_fuego`, `invocar_cuerpo`, handlers en `machine.py`).

## D7 — Métricas A/B
Variables: tasa FP (primaria), coste/hallazgo (secundaria). Control = mismo problema/artefacto/presupuesto. Aislamiento = sesiones separadas, semilla registrada. Posible `INCONCLUSIVE`. No implementado (experimentos A/B no ejecutados).
