# Finding 1620 — RXRE-EXT-006: `rxre repl` interactive loop with auto-reflection (AGUA)

**Fecha:** 2026-10-15
**Categoría:** tooling / CLI / repl / loop
**Autor:** OpenCode agent (iteración 8-principios)
**Estado:** ✅ completada

## Resumen

Se añade `op: repl` — un loop interactivo que ejecuta una secuencia de
operaciones (`steps`) y genera automáticamente una `reflexion_sugerida` cuando
una operación falla o se bloquea.

### BODY → MIND (§10)

El loop es **explícitamente abierto**: NO reintenta automáticamente. Cada fallo
produce una `reflexion_sugerida` que el llamante debe revisar antes de volver a
ejecutar. Esto evita el error F8 (exit 0 con salida incorrecta): el veredicto
nunca se impone, se propone.

### Distinguir `invalid_input` vs `blocked` (§10 TAXONOMÍA)

- `invalid_input` → el artefacto fue proveido pero es inválido (no existe, no
  es ELF, hash no coincide). Acción: `op:verify` con el mismo artefacto.
- `blocked` → la operación fue bloqueada antes de ejecutarse (parametros
  faltantes, allow-list, etc.). Acción: verificar parametros y reintentar.

## Principio asociado

**AGUA** (fluidez): el loop permite iterar rápidamente sin perder el hilo. Las
reflexiones se registran como hipótesis falsables, no como conclusiones
definitivas. El `session_id` (ALMA) se propaga a cada step para mantener la
continuidad del propósito.

## Evidencia

```
echo '{"op":"repl",
       "steps":[{"op":"verify","artefacto":"/bin/ls"},
                {"op":"discover","artefacto":"/bin/ls"}],
       "session_id":"test-rx550-001"}' | ./rxre
```

```json
{
  "status": "ok",
  "op": "repl",
  "session_id": "test-rx550-001",
  "steps_executed": 2,
  "steps_total": 2,
  "results": [
    {"index": 0, "op": "verify", "status": "ok", "summary": {...}},
    {"index": 1, "op": "discover", "status": "ok", "summary": {...}}
  ],
  "reflexiones": [],
  "stopped_at": null
}
```

## Modo fallo

Cuando un step falla, el loop se detiene (a menos que `continue_on_error=True`)
y genera:

```json
{
  "reflexiones": [{
    "step": 0,
    "op": "discover",
    "estado": "blocked",
    "motivo": "falta 'artefacto'",
    "reflexion_sugerida": "La operacion fue bloqueada: falta 'artefacto'. "
                         "Verificar parametros y reintentar con op:verify primero.",
    "accion_alternativa": "op:discover requiere artefacto ELF valido; "
                          "usar op:verify primero"
  }]
}
```

## Cambios

`tools/rxre/api/machine.py`:
- Añadido `_handle_repl()` y helpers `_sintetizar()`, `_accion_alternativa()`.
- Registrado en `HANDLERS` y en `op: ops`.
- Test actualizado: `cli.ops_tiene_verify`, `cli.ops_tiene_discover`,
  `cli.ops_tiene_repl`.