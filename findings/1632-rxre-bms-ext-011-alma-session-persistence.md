# Finding 1632 — RXRE-BMS-EXT-011: ALMA session persistence + resume in repl

**Fecha:** 2026-10-15  
**Categoría:** tooling / ALMA / persistence / session  
**Estado:** ✅ completada

## Resumen

`_handle_repl` ahora soporta `resume: true` para saltar steps ya completados en
una session anterior. La persistencia se basa en `execution_events.trace_id`
como session_id, sin necesidad de una tabla nueva.

## Principio

**ALMA** — Mantener objetivos globales, prioridades, restricciones y estado de
la investigación. La continuidad de propósito (§31) requiere que un agente
pueda retomar trabajo sin repetir lo ya hecho.

## Evidencia

```
Step 1: repl session=test, steps=[verify] → step0: ok
Step 2: repl session=test, resume=true, steps=[verify, ops]
  → step 0: completed (saltado, completado en session anterior)
  → step 1: ops -> ok
```

## Diseño

- `_persistir_session_steps(session_id, steps, results)`: inserta en
  `execution_events` con `trace_id=session_id`, `persistido=1` para cada step
  con status `ok`
- `_cargar_session_steps(session_id)`: querya `trace_id=session_id AND
  persistido=1` y devuelve lista de ops completados
- Limitaciones: solo salta steps con el mismo `op` exacto, no steps con
  parámetros diferentes. Para saltar por content hash, usar `evento_id` que
  es determinista por step_id.

## Cambios

`tools/rxre/api/machine.py`:
- `_handle_repl` acepta `resume: bool` (default false)
- Añadido `_persistir_session_steps()` y `_cargar_session_steps()`
- Los steps completados se saltan con status `completed` y summary
  `"saltado (completado en session anterior)"`
