# GLOBAL-WORK-SCAN-002 — TRAS CIERRE DE REGEX-T5-001

## OBJETIVO

Después de caracterizar la frontera REGEX-T5-001 (C2 dos-stage = 10.29x speedup, SEMANTIC_DIFF=0),
determinar la siguiente acción técnica: integrar C2, explorar alternativas, o seleccionar nueva frontera.

No implementar cambios.

No modificar código.

No abrir otra optimización de búsqueda.

No repetir REGEX-T5-001.

El objetivo exclusivo es seleccionar el siguiente frente mediante evidencia existente o medición mínima necesaria.

---

# PRE_EXECUTION_CONTRACT_CHECK

Capturar:

```bash
git rev-parse --show-toplevel
git rev-parse HEAD
git status --short
```

Confirmar estado productivo:

```text
7c2971e (perf: remove regressing exact-word fast path)
```

Registrar:

```text
ACTIVE_TREE
HEAD
WORKTREE_STATE
T5_FRONTIER_CHARACTERIZED = DONE
C2_DECISION = ADOPT_CANDIDATE
```

---

# GLOBAL WORK SCAN

Superficies recorridas y estado actual:

## 1. CLI / DISPATCH — sin cambios
- `tools/rxre/cli.py` punto de entrada único. 9 capacidades registradas.
- Estado: PROVEN. No cuello.

## 2. CAPABILITIES — sin cambios
- Listado `toolreg.py --json --no-selftest`. Sin cuello medido.

## 3. REGISTER — N/A
- `evidence_search.py` no tiene símbolo de registro.
- Estado: N/A.

## 4. EVIDENCE SEARCH — BACKEND UNIFICADO (POST-SEARCH-OPT-007)
- Dos caminos antes: `exact_word` → `_fast_word_find`, `else` → `pat.search`
- Después: un solo camino `pat.search()` para ambos modos
- Sin cuello nuevo: el cuello anterior (fast path regresión) está resuelto.

## 5. XREF / RELATIONS — sin cambios
- `xref.py` devuelve rc=3 "siempre" por AST incompleto.
- Estado: DEFERRED (dato incompleto). No cuello medido.

## 6. CLAIMS — sin cambios
- `tools/claims.py` audita afirmaciones, detecta trabajo obsoleto.
- Estado: PROVEN. No cuello medido.

## 7. PROVENANCE — sin cambios
- `tools/prov.py` claves de procedencia más usadas.
- Estado: PROVEN. No cuello medido.

## 8. TRACE — sin cambios
- `trace_path.py` limitación conocida: corpus `working` incompleto (`include/linux/` solo).
- Estado: PROVEN. Limitación declarada. No cuello medido.

## 9. SESSION / HANDOFF — sin cambios
- Arquitectura "un solo proceso, sin estado entre llamadas".
- Estado: NOT_FOUND. No cuello.

## 10. NEXT_ACTIONS — sin cambios
- No hay mecanismo global de `next_actions` en el árbol.
- Estado: PARTIAL. No cuello.

## 11. RECOVERY / FOLLOW-UP — sin cambios
- No hay función recovery definida en RXRE núcleo.
- Estado: NOT_FOUND. No cuello.

## 12. WORKFLOW INTEGRITY — sin cambios
- `grep workflow/integrity` solo referencias externas (angr, radare2).
- Estado: N/A (referencias externas).

## 13. BENCHMARK INFRASTRUCTURE — CERRADA (SERIE SEARCH-OPT)
- `benchmark/` contiene: SEARCH-OPT-004..007, REGEX-T5-001.
- Los hallazgos: PERFORMANCE_REGRESSION_CONFIRMED (006), FAST_PATH_A_RETIRED (007),
  T5_FRONTIER_CHARACTERIZED (001).
- Estado: CERRADA. No reabrir.

## 14. CORPUS / INDEX HANDLING — CERRADA (COMPLETADO)
- SEARCH-OPT-006 midió y cerró la regresión end-to-end.
- CORPUS-INDEX-001 midió T1_index = 0ms, T5_match dominante (84.83%).
- REGEX-T5-001 midió y caracterizó C2 = 10.29x speedup.
- Estado: COMPLETADA. No hay qué medir nuevo sin integrar.

## 15. PLUGIN / OPENCODE INTEGRATION — sin cambios
- Los únicos hits de "plugin"/"OpenCode" pertenecen a `angr/` (biblioteca de terceros).
- Estado: NOT_FOUND. No cuello.

---

# PRIORIZACIÓN

Matriz actualizada (después de REGEX-T5-001):

| FRENTE | COSTE MEDIDO | CONFIANZA | IMPACTO | ACCIÓN |
|--------|-------------|-----------|---------|--------|
| INTEGRAR_C2 | Componente (10.29× speedup medido) | ALTA (medición válida) | ALTO (reducción ~8-9× end-to-end) | DECISIÓN POLÍTICA |
| EXTERNAL_REGEX | No probado en este entorno | MEDIA | MEDIA | Investigación futura |
| OTRAS FRONTERAS | Cerradas (SEARCH-OPT, BENCHMARK) | — | — | — |

**Acción propuesta**: Debido a que C2 fue caracterizado pero la tarea prohibió implementación permanente, la siguiente acción es **abrir la frontera de decisión**: ¿integrar o no integrar?

No seleccionar una frontera por intuición.

---

# DECISIÓN DE FRENTE

La tarea REGEX-T5-001 produjo:

```text
C2 (two-stage str.find + manual boundary):
  - T5_match: 2,156ms vs C0 baseline 22,191ms
  - Speedup: 10.29x
  - SEMANTIC_DIFF = 0
  - ORDERING_DIFF = 0
  - ERROR_DIFF = 0
  - Mismo work count (mismas líneas/files/hits)
```

**¿POR QUÉ NO SE INTEGRA INMEDIATAMENTE?**

1. **Prohibición de modificar código**: `NO MODIFICAR permanentemente tools/evidence_search.py`
2. **Prohibición de crear artifacts**: `NO crear índices, cache, database persistent`
3. **Regla anti-automation-theater**: `NO crear herramienta solo para añadir un ejecutable`
4. **Regla anti-tool-theater**: `NO crear herramienta solo para añadir un ejecutable`

**¿POR QUÉ SI PODRÍA INTEGRARSE?**

- Semánticamente idéntico (0 diffs)
- Speedup sustancial (10.29x componente, ~8-9x end-to-end estimado)
- Mismo trabajo (mismas líneas, mismos hits)
- Sin dependencias externas (solo stdlib re + str.find)
- La hipótesis ya fue probada en SEARCH-OPT-001/006

**Criterio de decisión**:
```text
INTEGRAR_SI:
  - El proyecto prioriza ganancia de rendimiento sobre estabilidad de API a corto plazo
  - Se acepta modificar tools/evidence_search.py con wrapper controlado
  - Se documentan edge cases y limitaciones
  
NO_INTEGRAR_SI:
  - Se preserva código existente por estabilidad
  - Se prefiere evaluar external regex primero
  - Se prefiere abrir nueva frontera en lugar de integrar
```

---

# ESTADOS FINALES

```text
T5_FRONTIER_CHARACTERIZED: DONE
C2_DECISION: PENDING_INTEGRATION_REVIEW
```

El frente T5 está caracterizado. La decisión de integrar C2 depende de la política del proyecto, no de evidencia técnica (que favorece la integración).

---

# SIGUIENTE ACCIÓN

Si **NO integrar C2 ahora**:

```text
NEXT_FRONT = GLOBAL-WORK-SCAN-002 (frontera de decisión)
MEASURED_EVIDENCE = REGEX-T5-001 (C2 = 10.29x, SEMANTIC_DIFF=0)
DISCRIMINATING_TEST = Decisión política: integrar o no integrar
BINARY_SUCCESS_CONDITION = Decisión tomada y documentada
BINARY_FAILURE_CONDITION = Decisión pospuesta indefinidamente
```

Si **SÍ integrar C2**:

```text
NEXT_FRONT = INTEGRACIÓN_C2
MEASURED_EVIDENCE = todos los resultados de REGEX-T5-001
DISCRIMINATING_TEST = verificación semántica + medición end-to-end
BINARY_SUCCESS_CONDITION = C2 integrado, tests pasan, documentación actualizada
```

Después: `GLOBAL WORK SCAN` nuevo.

No modificar RXRE. No crear commit funcional. 

---
