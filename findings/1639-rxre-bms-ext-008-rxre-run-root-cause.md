# Finding 1622 — RXRE-EXT-008: root-cause analysis in `op:run` (MENTE)

**Fecha:** 2026-10-15
**Categoría:** tooling / CLI / root-cause / causality
**Estado:** ✅ completada

## Resumen

`_handle_run` ahora incluye `root_cause` en su respuesta cuando la operación
devuelve `blocked`, `invalid_input` o `error`. El análisis no produce un
veredicto — produce una **hipótesis falsable** con una acción de verificación
concreta.

## Principio

**MENTE**: "toda afirmación lleva su por qué, y hay un control negativo."
§48 exige un discriminante. Un veredicto que no puede refutarse no es un
mecanismo. `root_cause` propone hipótesis con `verificacion` concreta, no
una conclusión.

## Clasificación de fallos

| Tipo | Condición | Verificación |
|---|---|---|
| `not_in_registry` | capability no existe en el registry | `op:backends` para listar capabilities |
| `missing_param` | faltan parámetros obligatorios (artefacto) | `op:verify --artefacto <ruta>` |
| `backend_unavailable` | precheck `backend_existe=False` | `op:verify` para confirmar PATH |
| `artefacto_not_found` | precheck `input_existe=False` | `op:verify --artefacto <ruta>` |
| `producer_error` | exit_status del backend ≠ 0 | ejecutar manualmente con -v |
| `undetermined` | no encaja en patrones conocidos | `op:explain --root_cause` |

## Evidencia

```json
{
  "op": "run",
  "capability": "binary.no_existe",
  "status": "blocked",
  "motivo": "no hay ninguna capacidad registrada llamado 'binary.no_existe'",
  "root_cause": {
    "env_status": "blocked",
    "env_motivo": "no hay ninguna capacidad registrada...",
    "hipotesis": [{
      "nodo": "dispatch.esta_permitida",
      "tipo": "not_in_registry",
      "hipotesis": "La capability solicitada no esta en el registry",
      "verificacion": "Consultar op:backends para ver capabilities disponibles",
      "veredicto": "refutar: listar capabilities y confirmar que el nombre existe"
    }],
    "n_hipotesis": 1,
    "veredicto": "investigar"
  }
}
```

## Cambios

`tools/rxre/api/machine.py`:
- Añadida `_analyze_run_failure(env)` — analiza motivo, precheck, exit_status
- `_handle_run` ahora incluye `root_cause` en la respuesta cuando falla
- Distingue `blocked` vs `invalid_input` (§10 TAXONOMÍA)