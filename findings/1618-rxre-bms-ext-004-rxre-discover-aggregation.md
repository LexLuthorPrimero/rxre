# Finding 1618 — RXRE-EXT-004: `rxre discover` aggregation (ETER)

**Fecha:** 2026-10-15
**Categoría:** tooling / CLI / aggregation
**Autor:** OpenCode agent (iteración 8-principios)
**Estado:** ✅ completada

## Resumen

Se añade `op: discover` al motor RXRE, que encadena tres capabilities sobre un
mismo artefacto y agrega los resultados en un solo envelope de findings:

1. **binary.inspect** — metadatos del ELF, funciones detectadas.
2. **binary.xrefs** — referencias cruzadas (DATA/CALL/JUMP).
3. **binary.callgraph** — grafo de llamadas entre funciones.

## Principio asociado

**ETER** (conexión universal): nada se queda aislado. Cada símbolo nuevo es
una *frontier* abierta (§53); cada xref es una arista; cada función del
callgraph es un nodo. El descubrimiento los integra en una sola respuesta para
evitar que el investigador tenga que lanzar 3 comandos por separado.

## Evidencia

```
echo '{"op":"discover","artefacto":"/bin/ls"}' | ./rxre
```

```json
{
  "status": "ok",
  "capability": "binary.discover",
  "artefacto": "/bin/ls",
  "ejecutada": true,
  "findings": [
    {"finding_type": "binary_functions", "source": "binary.inspect", "n": 1, "estado": "ok"},
    {"finding_type": "binary_xrefs", "source": "binary.xrefs", "n": 74, "estado": "ok"},
    {"finding_type": "binary_callgraph", "source": "binary.callgraph", "n": 5, "estado": "ok"}
  ],
  "total_symbols": 80,
  "provenance": {
    "estado": "completa",
    "transformacion": "discover = binary.inspect + binary.xrefs + binary.callgraph -> agregacion de findings",
    "normalizador": "machine._handle_discover"
  }
}
```

## Diseño

`discover` **no es un productor**: no ejecuta backends directamente. Delega a
`dispatch.ejecutar()` para cada capability y agrega los resultados. Esto
preserva la trazabilidad: cada finding incluye `source` y `estado` para que se
pueda reconstruir la cadena con `op: explain <result_id>`.

## Cambios

`tools/rxre/api/machine.py`:
- Añadido `_handle_discover()` que orquesta los 3 adapters.
- Registrado en `HANDLERS` y en `op: ops`.