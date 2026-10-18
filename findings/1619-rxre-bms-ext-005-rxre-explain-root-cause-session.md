# Finding 1619 — RXRE-EXT-005: `rxre explain` root-cause + session tracking (TIERRA/MENTE/ALMA)

**Fecha:** 2026-10-15
**Categoría:** tooling / CLI / explain / root-cause
**Autor:** OpenCode agent (iteración 8-principios)
**Estado:** ✅ completada

## Resumen

Se potencia `op: explain` con tres modos nuevos, activables por parámetros:

| Parámetro | Principio | Función |
|---|---|---|
| `root_cause=True` | **MENTE** (causalidad) | Analiza la cadena del backend (`cadena_backend`) y el estado del resultado para proponer hipótesis falsables sobre la causa raíz del bloqueo/fallo. |
| `session_id=...` | **ALMA** (continuidad) | Registra una sesión de trabajo en la tabla `research` para rastrear el propósito a través de múltiples operaciones (§31). |
| `audit_truncation=True` | **AIRE** (transparencia) | Audita truncamientos y datos corruptos (strings truncados, profundidad excesiva, dumps no truncados). |

## Principio asociado

- **TIERRA** (linaje): `explain` ya reconstruía la cadena de evidencia; ahora
  incluye el análisis causal completo.
- **MENTE** (mente): la causa raíz no es un veredicto, es una hipótesis
  falsable con acción de verificación concreta. Cada hipótesis incluye:
  - `nodo`: qué paso de la cadena se examina.
  - `tipo`: categoría de fallo (`blocked`, `invalid_input`, `empty_result`,
    `backend_blocked`, `backend_error`, `unverified_version`).
  - `evidencia`: lo que la base afirma.
  - `hipótesis`: lo que se infiere.
  - `verificación`: acción para confirmar o refutar (open-loop: no es un
    veredicto, es un plan de verificación).
- **ALMA** (alma): la sesión agrupa operaciones con un propósito común,
  manteniendo la continuidad de la intención a través del tiempo.
- **AIRE** (aire): la auditoría de truncamiento previene el error F8: un
  string de 57630 chars puede ser un dump no truncado que un agente
  interpretaría como "todo OK" cuando en realidad la salida fue truncada.

## Evidencia

```
echo '{"op":"explain","result_id":"res_xref_d684f9cac34ede50","root_cause":true,"audit_truncation":true}' | ./rxre
```

```json
{
  "status": "ok",
  "root_cause": {
    "result_id": "res_xref_d684f9cac34ede50",
    "hipotesis": [{
      "nodo": "result.status",
      "tipo": "ok",
      "evidencia": "observed",
      "hipotesis": "El resultado es ok — no hay causa raiz de fallo",
      "verificacion": "No se necesita accion correctiva..."
    }],
    "n_hipotesis": 1,
    "veredicto": "completo"
  },
  "truncation_audit": {
    "ok": false,
    "max_depth": 4,
    "max_len": 57630,
    "issues": ["string muy largo: 57630 chars (posible dump no truncado)"]
  }
}
```

## Cambios

`tools/rxre/api/machine.py`:
- Añadidos `_analyze_root_cause()`, `_auditar_truncamiento()`,
  `_registrar_sesion()`.
- Modificado `_handle_explain()` para aceptar los nuevos parámetros.
- Actualizado el listado de `op: ops`.