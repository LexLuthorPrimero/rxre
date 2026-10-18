# Finding 1633 — RXRE-BMS-EXT-012: AGUA auto-lesson-verification after reflect

**Fecha:** 2026-10-15  
**Categoría:** tooling / AGUA / lesson verification  
**Estado:** ✅ completada

## Resumen

`_handle_reflect` ahora llama a `store.verificar_lecciones()` después de
registrar una reflexión, incluyendo el estado global de lessons en la
respuesta. Esto conecta AGUA→AIRE: la lección registrada no queda aislada,
se verifica inmediatamente si está vigilada por un check ejecutable.

## Principio

**AGUA** — Convertir fallos en lecciones persistentes. **AIRE** — Verificar
contratos y el recorrido completo. Escribir una lección sin check es dejar un
dato; verificar que el check existe es cerrar el circuito.

## Evidencia

```json
{
  "op": "reflect",
  "feedback": "test reflection",
  "reflection": "the test failed because X",
  "outcome": "failure",
  "check_ejecutable": "tests/test_dummy.py::test_fail"
}
→ status: ok
→ vigilada: true
→ lecciones_verificadas: {"sin_check": 3, "vigiladas": true}
→ lecciones_total_sin_check: 3
```

## Cambios

`tools/rxre/api/machine.py`:
- `_handle_reflect` llama a `store.verificar_lecciones(c, ejecutar=False)`
  after successful registration
- Response incluye `lecciones_verificadas` (dict con `sin_check`, `vigiladas`)
  y `lecciones_total_sin_check` (int)
- El `next_actions` para `lessons` ahora incluye `ejecutar: true` para
  validación inmediata
