# 1621 — AGUA: tracking de aplicación de lecciones (IMPLEMENTADO 2026-10-15)

- Fecha: 2026-10-15
- Clasificación: **DEMOSTRADA (mecanismo)** / **NO VERIFICADA (causalidad)**
- Prueba: `tools/rxre/tests/test_agua_application013.py` → 5/5

## Qué se implementó (opción A del diseño original)

| Paso | Dónde | Estado |
|---|---|---|
| 1. Migración idempotente `_asegurar_columnas_execution_events()` | `store.py` (llamada desde `conectar`) | hecho; añade `trace_id` y `lecciones_json` a bases viejas |
| 2. `registrar_evento` persiste los ids | `store.py :: registrar_evento` | hecho; extrae `reflexion_id` de dicts o usa strings |
| 3. `_handle_plan` incluye `reflexion_id` en `reflexiones_previas` | `machine.py` | hecho (antes llevaba outcome/feedback/reflection/strategy/intento sin id) |
| 4. `trazar_aplicacion_lecciones(c, capability)` read-only | `store.py` | hecho; devuelve `surfaceada` / `candidate_aplicada` / `sin_datos` |
| 5. `_handle_plan` arreglado | `machine.py` | BUG MEDIDO Y CORREGIDO: usaba `c` después de `c.close()` (el `finally` cerraba antes), así que **nunca** se registró ni un evento `op=plan`. Ahora abre su propia conexión |

## Discriminante corrido (test_agua_application013.py)

- **H1**: un evento `plan` con lección → `lecciones_json` contiene el id y
  `trazar_aplicacion_lecciones` la reporta `surfaceada`. PASS
- **H2**: capability sin lecciones → `sin_datos` (empty). PASS
- **H3**: `plan` solo surfacea; `candidate_aplicada=True` requiere un `run`
  POSTERIOR de la misma capability con `exit_status=0`. PASS
- **NEG**: run posterior con `exit_status=1` NO produce candidata. PASS

## Estado medido tras la implementación (DB viva)

```
op=plan: 1+   (antes 0: el bug del finally tapaba el registro)
op=run:  76+
```

## Lo que sigue siendo NO VERIFICADO (honestidad)

- **Causalidad**: `candidate_aplicada` es INDICIO (run OK posterior), no
  prueba de que la lección causara el éxito. La causalidad lección→resultado
  no es medible con estos datos.
- **`trace_id`**: sigue sin productor de negocio que lo escriba desde el
  agente (OpenCode no expone su tool-call a un script); la columna existe,
  la migración ya la mantiene.
- **Exposición CLI**: `trazar_aplicacion_lecciones` es función de store; no
  hay todavía una `op:` que la exponga (pendiente `op:application-tracking`
  o similar).

## Regresión de suites (tras el cambio)

- cli009 91/91, backends004 159, agua_plan008 4/4, lecciones006 7/7,
  eventlog006 4/4, eter_correlation011 7/7, aire_consistencia012 9/9,
  aether008 23/23, autonomy003 11/11, eco_principios002 39/39.
