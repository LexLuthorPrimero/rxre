# Finding 1623 — RXRE-EXT-009: auto-reflection when gate fails (AGUA)

**Fecha:** 2026-10-15
**Categoría:** tooling / CLI / auto-reflection / learning
**Estado:** ✅ completada

## Resumen

Cuando el gate (8 principles) rechaza una operación (`operacion_cerrada=False`
con `violation`), `_handle_run` ahora registra **automáticamente** una fila en
`reflexiones` con:

- `feedback`: la(s) violación(es) del gate
- `reflection`: el motivo de la violación
- `outcome`: `failure`
- `attempt_id`: el `operation_id` (si existe)
- `capability`: la capability ejecutada

Esto cierra el lazo **AGUA → MENTE → FUEGO**: el fallo se registra como
lección, y futuras ejecuciones de la misma capability consultan
`consultar_reflexiones_para_capability()` antes de ejecutar (ya implementado
en `_handle_run` L634).

## Principio

**AGUA**: "convertir fallos y hallazgos confirmados en lecciones persistentes
que cambien decisiones futuras."

## Evidencia del ciclo completo

1. **FUEGO**: `run binary.xrefs` → producer OK → gate evalúa → 8/8 pass → persistido ✅
2. **FUEGO**: `run binary.some_bad_cap` → producer error → gate violation
3. **AGUA**: `_auto_registrar_reflexion_gate()` → registra reflexión con feedback
4. **ALMA**: reflexión enlazada a capability + target
5. **AGUA→FUEGO**: próxima `run binary.xrefs` consult `consultar_reflexiones` → muestra warning

## Cambios

`tools/rxre/api/machine.py`:
- Añadida `_auto_registrar_reflexion_gate(env, capability)`
- `_handle_run` llama a `_auto_registrar_reflexion_gate()` cuando
  `gate.operacion_cerrada=False` y `env.status=="ok"` y hay results

## Relación con el AGUA→MENTE→FUEGO loop existente

El sistema YA tenía:
- AGUA→FUEGO: `_handle_run` consulta `consultar_reflexiones_para_capability` antes de ejecutar (L634)
- MENTE→ALMA: `_handle_plan` incluye `reflexiones_previas` en el plan (L803)

Ahora se añade:
- FUEGO→AGUA: cuando el gate falla, se registra una reflexión automáticamente

Esto cierra el ciclo completo.