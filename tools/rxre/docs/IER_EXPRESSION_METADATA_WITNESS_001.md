# IER-EMW-001 — Testigo de preservación de metadatos en IR

**Estado de la capacidad RXRE:** `PARTIAL`.
**Caso motivador:** [angr #7013](https://github.com/angr/angr/issues/7013), revisado el 2026-11-18.
**Problema upstream:** issue abierto; GitHub no muestra una rama o pull request asociado en este corte.
**Alcance:** comprueba que campos de metadatos seleccionados se preserven entre una expresión IR antes y después de una reescritura.

## Incidencia investigada

El issue informa que dos motores de reescritura de AIL (`ssailification` y `dephication`) reconstruyen un `BinaryOp` cuando cambia uno de sus operandos, pero no reenvían `vector_count` ni `vector_size` al constructor. Los valores por defecto reemplazan la forma vectorial original por `None`, mientras que `bits` sí se mantiene. La incidencia señala que un consumidor de `InterleaveLOV` requiere esos dos campos y puede fallar después de la reescritura.

El reporte incluye un reproducer determinista sobre la construcción de un único `BinaryOp`; no depende de un binario. También identifica el patrón de reparación: preservar `vector_count=expr.vector_count` y `vector_size=expr.vector_size` en ambos sitios, como ya hace otro constructor del árbol.

La página del issue permanece abierta y sin PR enlazado en el corte consultado. Esto establece que GitHub no muestra allí una corrección propuesta, no que nadie haya trabajado en privado.

## Capacidad agregada a RXRE

`ier/expression_metadata_witness.py` expone:

- `audit_expression_metadata(case)`: compara los campos declarados de una expresión antes y después de la transformación.
- `ail_binaryop_vector_shape_case(...)`: construye un caso para el perfil `ail.binaryop.vector_shape`, que verifica `bits`, `vector_count` y `vector_size`.

El testigo requiere evidencia referenciada de ambos lados y banderas explícitas de completitud. Si un valor de origen es desconocido o alguna cobertura es incompleta, produce `BLOCKED / NOT_DETERMINED`. Ante valores conocidos que se perdieron o cambiaron, produce `FAIL / PARTIAL`. Si coinciden, produce `PASS / PARTIAL`; nunca emite `PROVEN`, porque confía en quien extrajo las expresiones y no verifica que la reescritura haya sido ejecutada.

La función acepta una lista de campos definida por el llamador, de modo que puede servir para otras familias de nodos IR con metadatos que deban sobrevivir una reconstrucción.

## Reproducción reducida

La prueba guarda un `BinaryOp("InterleaveLOV", bits=128, vector_count=16, vector_size=8)` y modela la reconstrucción reportada:

```text
antes:    bits=128, vector_count=16, vector_size=8
después:  bits=128, vector_count=None, vector_size=None
```

Ejecuta los dos caminos de reescritura en el modelo y comprueba que ambos fallen por los dos campos omitidos. Una segunda variante preserva los tres y debe dar `PASS` dentro del scope declarado.

```bash
python3 -B tools/rxre/tests/test_expression_metadata_witness.py
```

Esto valida el auditor y el reproducer reducido de la condición descrita. No es una ejecución contra los motores upstream instalados ni un parche aplicado al repositorio angr.

## Intervención upstream sugerida

En cada constructor de `BinaryOp` de los dos reescritores, reenviar los metadatos vectoriales del nodo original junto a `bits`, `floating_point` y `rounding_mode`:

```python
vector_count=expr.vector_count,
vector_size=expr.vector_size,
```

La validación upstream debería probar cada motor con un operando que se reescribe y confirmar que la expresión resultante mantiene `bits`, `vector_count` y `vector_size`. Un test adicional con un consumidor que aserte la forma de vector serviría como oráculo del efecto downstream.

## Límites

- La capacidad es un comparador de snapshots suministrados; no instrumenta automáticamente SSA ni dephication.
- `PASS` cubre solo campos, expresiones y snapshots declarados.
- La pérdida modelada de `vector_count`/`vector_size` coincide con el antes/después publicado en el issue, pero el parche upstream no se aplicó ni se verificó desde este checkout.
- No se declara impacto de ejecución observado; el issue describe una condición que afecta al consumidor vectorial cuando dicho metadato se necesita.

## Fuente

- [angr issue #7013](https://github.com/angr/angr/issues/7013)
