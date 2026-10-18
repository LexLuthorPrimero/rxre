# Finding 1621 — RXRE-EXT-007: `rxre select` mission/task selector (ALMA/ETER)

**Fecha:** 2026-10-15
**Categoría:** tooling / CLI / mission / task
**Estado:** ✅ completada

## Resumen

Se expone `store.seleccionar_siguiente_accion()` como `op: select`, cerrando
la carencia de que el sistema de misiones/tareas no fuera accesible desde CLI.

`select` ordena tareas por **valor real** (no por prioridad entera) usando
`valorar_tareas()` que considera:

| Componente | Qué mide |
|---|---|
| desbloquea | cuántas tareas PENDING dependen de esta |
| bloqueada | si las dependencias están completadas (puerta, no puntuación) |
| incertidumbre | research abierta sobre el target |
| evidencia_ausente | findings sobre el target |
| reincidencia | reflexiones de fallo sobre el target |
| alineación | criteria que mencionan el target |
| coste | AVAILABLE=0.0, PARTIAL=0.5, no-ejecutable=1.0 |

## Uso

```
echo '{"op":"select"}' | ./rxre    # crea misión DEFAULT, devuelve siguiente tarea
echo '{"op":"select","mission_id":"mission_abc"}' | ./rxre
echo '{"op":"select","target":"binary.xrefs"}' | ./rxre  # registra frontier + select
```

## Evidencia

```
{"op":"select","target":"binary.xrefs"}
→ status: empty, mission_id: mission_xxx, next_actions: [research]
(Sin tareas → sugiere registrar una frontier)
```

## Principios

- **ALMA**: mantiene objetivos globales (misiones) y estado de investigación
- **ETER**: selecciona el siguiente trabajo globalmente útil, no localmente obvio

## Cambios

`tools/rxre/api/machine.py`:
- Añadido `_handle_select()` + helper `_capability_de()`
- Registrado en HANDLERS (14 ops) y en `op: ops` listing