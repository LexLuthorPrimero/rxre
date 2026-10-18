# REPO-MIGRATION-003 — PORTAR TRABAJO VALIDADO AL RXRE ACTIVO

## OBJETIVO

Integrar en `/home/lucas/Escritorio/rxre` (activo) el trabajo técnico validado realizado en `/home/lucas/Escritorio/RX550-INVESTIGACION` (legacy).

## MIGRATION STATE

```
ACTIVE_REPO = /home/lucas/Escritorio/rxre
ACTIVE_BRANCH = migration/validated-legacy-work
ACTIVE_HEAD = 9ce74c5 (migration/validated-legacy-work)

LEGACY_REPO = /home/lucas/Escritorio/RX550-INVESTIGACION
LEGACY_HEAD = e99a0ad1fb92b97bec1615bbf650a0e88cdf7558
LEGACY_BRANCH = main
```

## COMMITS MIGRADOS

### 1. e99a0ad — fix: resolve trace enum definitions from corpus

**Origen:** legacy `e99a0ad1fb92b97bec1615bbf650a0e88cdf7558`
**Método:** cherry-pick a `migration/validated-legacy-work`
**Target SHA:** `12a3462455fc9b6caa0b41a86ffa096047c22168`

**Cambios incluidos:**
- `tools/trace_path.py`: resolver con fallback, provenance tracking
- `benchmark/DOGFOOD-002.md`: report completo (458 líneas)
- `benchmark/dogfood-002/rxre-outputs/`: 3 artefactos de replay

**Features preservadas:**
- `resolve_enum_definition()`
- `KNOWN_PATH` fallback
- `CORPUS_SEARCH` fallback
- `AMBIGUOUS_SYMBOL` rejection
- `NOT_FOUND` (corpus absence, not symbol absence)
- provenance: archivo, línea, símbolo, corpus, fuente

### 2. 97bae69 — perf: add exact-word search fast path

**Origen:** legacy `97bae69440e32e56b34f23946e8a3fad12427284`
**Método:** cherry-pick con resolución de conflicto
**Target SHA:** `9ce74c5`

**Cambios incluidos:**
- `tools/evidence_search.py`: fast path exact_word

**Conflictos:**
- `tools/evidence_search.py`: conflicto de fusión resuelto
- Mantenido: versión con fast path activo

## VALIDACIÓN

| Gate | Resultado |
|---|---|
| TRACE_RESOLUTION | PASS |
| PROVENANCE | PASS |
| RXRE_REGRESSION | PASS (38/38 selftest) |
| DOGFOOD_REPLAY | PASS |
| AMBIGUOUS_SYMBOL | PASS |
| NOT_FOUND | PASS |
| SEMANTIC_DIFF | 0 |
| ORDERING_DIFF | 0 |
| ERROR_DIFF | 0 |

## NO MIGRADOS (excluidos)

- RELATION_GAP (no es parte de DOGFOOD-002)
- P003 (no es parte de DOGFOOD-002)
- Cambios no commiteados del legacy (concurrentes)
- Benchmarks históricos (se preservan como HISTORICAL_EVIDENCE)

## ARTEFACTOS

- `benchmark/REPO-MIGRATION-003.md` (este informe)
- `benchmark/REPO-MIGRATION-003/commit-map.json`
- `benchmark/REPO-MIGRATION-003/file-map.json`
- `benchmark/REPO-MIGRATION-003/patch-map.json`
- `benchmark/REPO-MIGRATION-003/migration-matrix.json`
- `benchmark/REPO-MIGRATION-003/validation.log`

## ESTADO FINAL

```
MIGRATION_COMPLETE
```

## NOTA SOBRE COMMIT REUSE

Los SHAs legados NO se reutilizan en rxre. Los cambios fueron portados
con nuevos SHAs para evitar colisiones con la historia propia de rxre.
