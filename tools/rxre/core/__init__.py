#!/usr/bin/env python3
"""RXRE-1638. Capa de persistencia mínima para resultados de investigación.

ESTADO: esta capa NO existía. `rz_inspect.persistir()` hace `from core import
store as S` y el módulo no estaba. Consecuencia directa: `dispatch.ejecutar()`
devolvía `persistido: False` para CUALQUIER adapter que pasara por `_persistir()`
(rizin, radare2, Ghidra, Coccinelle — todos los que no son `rz_inspect` directo).
El resultado se perdía sin que nada lo notara, y `explain <result_id>` no
existía.

Implementación mínima, sin framework, sin base de datos externa:
- SQLite embebido en un archivo `.db` en el árbol.
- Dos tablas: `operations` (una fila por investigación) y `results` (una fila por
  resultado, con su `result_id` determinista).
- `conectar()` abre (o crea) la base.
- `registro()` inserta una operación y sus resultados.
- `recuperar(op_id)` devuelve la fila completa para que `explain` la reconstruya.

No se añade scoring, cache, graph, planner ni nada que no sea necesario para
satisfacer el contrato demostrado por el Experimento A: producir, persistir,
recuperar y verificar una afirmación.
"""