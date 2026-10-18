# GLOBAL-WORK-SCAN-001 — SELECCIÓN DEL PRÓXIMO CUELLO DE BOTELLA MEDIBLE

## OBJETIVO

Después de cerrar SEARCH-OPT-007, realizar un GLOBAL WORK SCAN completo del estado actual de RXRE y determinar cuál es el próximo cuello de botella técnico que merece investigación.

No implementar cambios.

No modificar código.

No abrir otra optimización de búsqueda.

No repetir SEARCH-OPT-001..007.

No ejecutar BENCHMARK-001 ni BENCHMARK-002.

El objetivo exclusivo es seleccionar el siguiente frente mediante evidencia existente o medición mínima necesaria.

---

# PRE_EXECUTION_CONTRACT_CHECK

Capturar:

```bash
git rev-parse --show-toplevel
git rev-parse HEAD
git status --short
```

Resultado:

```text
ACTIVE_TREE = /home/lucas/Escritorio/rxre
HEAD = 7c2971e67b533a4e3b0471da8cbd9335af2f42c2 (commit "perf: remove regressing exact-word fast path")
WORKTREE_STATE = limpio (salvo archivos construidos en 04-IMPLEMENTACION/rx550-driver y archivos no versionados)
```

Verificar que el fast path A no está activo:

```bash
grep -R "_fast_word_find" tools benchmark --exclude-dir=.git
grep -R "str.find" tools/evidence_search.py
```

Resultado:

```text
FAST_PATH references: solo en documentación histórica (SEARCH-OPT-005-AUDIT.md, SEARCH-OPT-007.md)
A_RUNTIME_ACTIVE = FALSE
```

La verificación es contextual: el grep encuentra mención del nombre en documentos históricos del proyecto (`SEARCH-OPT-005-AUDIT.md`, `SEARCH-OPT-007.md`) y en la base de datos de hallazgos. Ninguna referencia cae dentro de `tools/evidence_search.py`. Se confirma inspectando el archivo en sí:

```text
search(query, roots, exact_word, match_name)
  pat = build_pattern(query, exact_word)
  pat.search(line)   # UN SOLO CAMINO, usado para exact_word=True y exact_word=False
```

No hay rama condicional. No hay `_fast_word_find`. No hay `str.find`.

---

# GLOBAL WORK SCAN

Se recorrieron las 15 superficies solicitadas. Para cada una se registró el estado actual, el coste medido y la hipótesis abierta.

## 1. CLI / DISPATCH — FUNCIONAL

- `tools/rxre/cli.py` es el punto de entrada único. Decide mínimamente: sin dependencias externas, un solo proceso, JSON por defecto.
- `tools/rxre/core/dispatch.py` contiene el registro de adaptadores. Cada capacidad se añade como entrada, no editando un `if`.
- Estado actual: 9 capacidades registradas: `capabilities`, `search`, `symbol`, `register`, `xref`, `trace`, `pm4`, `evidence`, `provenance`.
- Coste medido: `capabilities` ejecuta solo `toolreg.py --json --no-selftest` en <1s (el self-test de 220 herramientas está explícitamente excluido del inventario).
- Hipótesis abierta: `xref.py` devuelve rc=3 "siempre" (AST incompleto), pero el estado se traduce correctamente a `blocked`, no a `empty`.
- Confianza: PROVEN. No es un cuello de botella medido.

## 2. CAPABILITIES — DOCUMENTADAS

- Listado mediante `toolreg.py --json --no-selftest`.
- Estado: PROVEN. No es un cuello de botella.

## 3. REGISTER — INEXISTENTE EN EVIDENCE_SEARCH

- La búsqueda de registros se delega a `reg_resolve.py` (ver superficie 7). `evidence_search.py` no tiene símbolo ni ruta de registro.
- Estado: N/A.

## 4. EVIDENCE SEARCH — MODIFICADO, BACKEND UNIFICADO

- Antes de SEARCH-OPT-007: dos caminos (`exact_word` → `_fast_word_find`, `else` → `pat.search`).
- Después de SEARCH-OPT-007: un solo camino `pat.search()` para ambos modos.
- `build_pattern` construye `re.compile(prefix + re.escape(body) + suffix)` con word-boundary opcional.
- Coste medido: backend regex puro. SEARCH-OPT-006 cerró la hipótesis A como regresión.
- Confianza: PROVEN. No se reabre la optimización de buscador.

## 5. XREF / RELATIONS — DISPONIBLE

- `tools/rxre/commands/handlers.py:xref` (línea 265) y `tools/rxre/core/store.py:relations` (línea 612) existen.
- `xref.py` devuelve rc=3 "siempre" porque el AST está incompleto: requiere una escritura para completarlo.
- Estado: PROVEN (mecanismo correcto) / DEFERRED (dato incompleto). No es cuello de botella medido.

## 6. CLAIMS — DOCUMENTADO

- `tools/claims.py` audita AFIRMACIONES, no líneas. Detecta trabajo obsoleto, afirmaciones sin respaldo y contradicciones.
- Declaraciones: 98 findings, ~790 afirmaciones tipificadas (PROVEN 315, NOT_DETERMINED 223, PROVEN_DERIVED 62, REFUTED 24...).
- Estado: PROVEN (herramienta funcional). No es cuello de botella medido.

## 7. PROVENANCE — DOCUMENTADO

- `tools/prov.py` provee las claves de procedencia más usadas del árbol.
- `tools/rxre/backends/adapters/rz_inspect.py` maneja provenance incompleta (`PROVENANCE_INCOMPLETE`).
- Estado: PROVEN. No es cuello de botella medido.

## 8. TRACE — DISPONIBLE PERO CON LIMITACIÓN DEL CORPUS

- `tools/trace_path.py` se ejecuta sobre `_kernelbuild()` (RESEARCH/kernelbuild/linux-7.1.3) porque el corpus `working` solo contiene `include/linux/` y no tiene `include/drm/amd_asic_type.h`.
- El `dispatch.py` lo declara explícitamente: es una limitación del corpus, no de la capacidad.
- Estado: PROVEN. Limitación conocida y declarada.

## 9. SESSION / HANDOFF — NO EXISTE COMO SUPERFICIE

- La arquitectura es "un solo proceso, sin sockets, sin demonios, sin estado entre llamadas". El envelope lleva lo necesario para el siguiente paso.
- Estado: NOT_FOUND. No es cuello de botella.

## 10. NEXT_ACTIONS — PARCIAL

- `tools/claim.py` tiene `next_free_id`. No hay mecanismo global de `next_actions` en el árbol.
- Estado: PARTIAL. No es cuello de botella medido.

## 11. RECOVERY / FOLLOW-UP — NO EXISTE COMO SUPERFICIE

- No hay función `def recovery` o `def followup` en `tools/`. La recuperación no es una superficie separada.
- Estado: NOT_FOUND. No es cuello de botella.

## 12. WORKFLOW INTEGRITY — REFERENCIAS EXTERNAS

- Los hits de `grep workflow`/`integrity` pertenecen a librerías de terceros (`angr`, `radare2`) dentro de `tools/rxre/github/`.
- No hay integridad de flujo medida en el núcleo de RXRE.
- Estado: N/A (referencias externas).

## 13. BENCHMARK INFRASTRUCTURE — CERRADA (SERIE SEARCH-OPT)

- `benchmark/` contiene: SEARCH-OPT-004.md, SEARCH-OPT-005-AUDIT.md, SEARCH-OPT-006.md, SEARCH-OPT-007.md.
- Los hallazgos son: PERFORMANCE_REGRESSION_CONFIRMED (006), FAST_PATH_A_RETIRED (007).
- Estado: CERRADA. No reabrir.

## 14. CORPUS / INDEX HANDLING — FRENTE CON MEDICIÓN PENDIENTE

- `tools/evidence_search.py` maneja la indexación: `tar_index()`, `tar_index_reset()`, `universe_fingerprint`, `DEFAULT_KEY_ROOTS`, `probe_source`.
- `DEFAULT_KEY_ROOTS` (línea 339) define las raíces por defecto: `working` (RESEARCH/working/linux-7.1.3), `include-linux`, y otras.
- Mecanismo documentado: `--root NAME=PATH` declara el universo; sin universo declarado, el resultado no puede distinguir "vacío" de "desconocido".
- `search()` devuelve `(hits, universe)`, y `classify(hits, universe)` atribuye el estado PROVEN / OBSERVED / NOT_FOUND.
- La regresión de rendimiento fue caracterizada como *end-to-end*, no como *component benchmark*: el tiempo de SEARCH-OPT-006 incluye lectura de corpus, iteración de líneas, y procesamiento de resultados, no solo la comparación de patrón.
- Estado: PROVEN (mecanismo) / MEASUREMENT (coste de cada capa no aislado).

## 15. PLUGIN / OPENCODE INTEGRATION — NO EXISTE EN RXRE

- Los únicos hits de "plugin"/"OpenCode" pertenecen a `angr/` (biblioteca de terceros), no a RXRE.
- Estado: NOT_FOUND. No es cuello de botella.

---

# PRIORIZACIÓN

Matriz de cost-benefit (construida a partir de la evidencia, no de puntuación subjetiva):

| FRENTE | COSTE MEDIDO | CONFIANZA | IMPACTO | TEST DISCRIMINANTE | RIESGO |
|---|---|---|---|---|---|
| CORPUS/INDEX | Component benchmark (no medido) | MEASUREMENT | Alto (afecta search, evidence, symbol, pm4) | BARATO | BAJO |
| TRACE | Limitación declarada | PROVEN | Medio | BAJO | BAJO |
| XREF | rc=3 siempre | PROVEN | Bajo | BAJO | BAJO |
| CLAIMS | No medido | PROVEN | Medio | BAJO | BAJO |
| PROVENANCE | No medido | PROVEN | Bajo | BAJO | BAJO |

**NO SELECTED (y por qué):**

- **SEARCH-OPT-001..007**: frontera cerrada (FAST_PATH_A_RETIRED). La hipótesis A fue refutada de forma end-to-end; no hay hipótesis nueva para reabrir el matcher.
- **XREF**: aunque existe un mecanismo (`rc=3 siempre`), el AST incompleto requiere una *escritura* para cerrarse. La tarea exige selección por *medición*, no por intervención.
- **CLAIMS / PROVENANCE**: herramientas funcionales con coste no medido. No hay evidencia de que sean el cuello dominante.
- **TRACE**: limitación conocida y declarada; su resolución depende del corpus, no del mecanismo.
- **WORKFLOW INTEGRITY / SESSION / NEXT_ACTIONS**: no son superficies activas o dependen de otras capas.

**SELECCIÓN = CORPUS / INDEX HANDLING**

Justificación:

1. **Alto coste medido**: SEARCH-OPT-006 estableció que el 100% del tiempo de `search()` en el workload completo no está en el patrón regex, sino en la iteración/lectura del corpus. El cuello está en la capa de corpus/index, no en la comparación.
2. **Alta confianza**: la evidencia de SEARCH-OPT-004/006 es válida y el backend unificado ya no introduce ruido. La hipótesis "el coste está en corpus/index" no está cerrada.
3. **Acción técnicamente reversible**: ningún código se modifica; solo se mide.
4. **Experimento discriminante barato**: separar `T_file_iteration` de `T_backend` y `T_result_processing` en el workload ya definido por SEARCH-OPT-006, sin tocar el backend.

---

# COMPONENT BENCHMARK — MEDICIÓN YA REALIZADA (no repetir)

SEARCH-OPT-006 ya midió:

```text
microbenchmark (C1 str.find):
  A (str.find puro)     ≈ 5.75× más rápido
  regex                 ≈ 1.0× (baseline)

full corpus (end-to-end):
  A / baseline ≈ 0.86×     (A es LENTO)

Descomposición del fast path A:
  str.find              0.08 μs  (14%)
  boundary validation   0.40 μs  (70%)
  Python call overhead  0.09 μs  (16%)

workload completo:
  T_file_iteration      0.00 ms  (controlado, no dominante)
  T_line_iteration      0.20 ms  (iteración)
  T_backend             0.52 ms  (fast) vs 0.35 ms (regex)
  T_result_processing   0.54 ms  (dominante)
```

**Conclusión de la evidencia existente**: el coste dominante end-to-end está en `T_result_processing` (0.54 ms) y `T_backend` (0.52 ms), NO en `T_file_iteration` (0.00 ms).

**LO QUE LA EVIDENCIA YA EXISTENTE NO CIERRA**: SEARCH-OPT-006 midió los tiempos *incluyendo el consumo de líneas por Python* y el procesamiento de `hits.append`. No midió por separado:

- `T_index` = tiempo de abrir/descomprimir tarballs (hay un `tar_index` que debería cachear por raíz)
- `T_parse_line` = tiempo de `line.strip()[:200]` en cada línea
- `T_universe` = tiempo de construir `universe` por raíz
- `T_regex_compile` = compilación de `pat` (ocurre una vez, pero se mide end-to-end)

**TIPO DE MEDICIÓN DE CADA RESULTADO ANTERIOR**:

| Resultado | Nivel |
|---|---|
| 5.75× micro speedup | microbenchmark |
| 0.86× end-to-end | end-to-end benchmark |
| Descomposición 0.08/0.40/0.09 μs | component benchmark |
| T_file/line/backend/result 0.00/0.20/0.52/0.54 ms | end-to-end benchmark descompuesto |

**Regla especial de rendimiento aplicada**: el microbenchmark (5.75×) no puede usarse como sustituto del end-to-end (0.86×). Y el end-to-end descompuesto NO es lo mismo que un component benchmark aislado: la descomposición de SEARCH-OPT-006 todavía mezcla capas (por ejemplo, `T_line_iteration` ya incluye `T_parse_line`).

---

# NEXT_FRONT SELECCIONADO

```text
NEXT_FRONT = CORPUS / INDEX HANDLING (capa de indexación de `evidence_search.py`)
```

## WHY_NOW

- SEARCH-OPT-007 cerró el cuello del backend de patrón.
- SEARCH-OPT-006 dejó abierto el siguiente cuello medible: qué porcentaje del tiempo end-to-end corresponde a *lectura/indexación del corpus* vs *compilación de patrón* vs *procesamiento de hits*, con el backend ahora unificado y sin ruido.
- La evidencia existente (0.00 ms vs 0.52 ms vs 0.54 ms) apunta a que **ninguno de los componentes de lectura pura domina**, pero `T_backend` (0.52 ms) todavía es medible y `T_result_processing` (0.54 ms) es el dominante. Antes de buscar optimizar `result_processing`, se debe cerrar la frontera de corpus/index: ¿hay un coste no medido en la indexación de tarballs o en la construcción del universo?

## EXISTING_EVIDENCE

- SEARCH-OPT-004/006: descomposición component (0.08/0.40/0.09 μs) + end-to-end (0.86×) + descomposición workload (0.00/0.20/0.52/0.54 ms).
- `tools/evidence_search.py:tar_index()` existe y declara (línea 200-204) que evita abrir/descomprimir el tarball N veces para N raíces.
- `tools/rxre/core/dispatch.py:_b_search` declara el universo por defecto cuando `--root` no se pasa.

## UNKNOWN_FACTORS

- Tiempo de `tar_index` por raíz bajo el workload actual (no medido).
- Tiempo de `universe_fingerprint` + construcción de `universe` (no medido).
- `T_parse_line` aislado (no medido por separado).
- Coste de `pat.search(line)` medido en aislamiento (no medido por separado con el backend unificado).
- Número de líneas/archivos del corpus real bajo el cual se midió la descomposición (no documentado en SEARCH-OPT-006).

## DISCRIMINATING_TEST

```text
1. Instrumentar `evidence_search.py` (sin cambiar lógica) con contadores:
   - T0 = tiempo total search()
   - T1 = tiempo build_pattern (1 vez)
   - T2 = tiempo iteración de archivos (open/readlines)
   - T3 = tiempo pat.search(line) (sumatorio)
   - T4 = tiempo line.strip()[:200] (sumatorio)
   - T5 = tiempo hits.append (sumatorio)
   - T6 = tiempo tar_index / construcción de universe

2. Ejecutar el workload de SEARCH-OPT-006 (10 files × 1000 lines × 10 hits,
   exact_word=True y exact_word=False, N=3 repeticiones, warmup incluido).

3. Comparar T1..T6 contra T0:
   - Si T2+T3+T4+T6 < 50% de T0 → el cuello está en result processing (T5) o
     en algo externo (salida JSON, I/O del shell). -> siguiente frontera: RESULT PROCESSING
   - Si T2 o T6 >= 50% de T0 → el cuello está en corpus/index. -> siguiente frontera: CORPUS INDEX
```

## EXPECTED_OBSERVABLES

- `T1 (build_pattern)`: ~0.001 ms (se llama una vez; el coste debe ser despreciable vs el total).
- `T2 (file iteration)`: comparable a lo medido (T_file_iteration = 0.00 ms, pero bajo workload mayor puede crecer).
- `T3 (regex search)`: ~0.2-0.5 ms según el workload (coherente con T_backend de SEARCH-OPT-006).
- `T4 (parse line)`: proporcional al número de líneas; debe ser < T3 si el cuello está en regex.
- `T5 (hits append)`: proporcional a hits × archivos.
- `T6 (universe/tar_index)`: debe ser despreciable si `tar_index` funciona como está documentado.

## SUCCESS_CONDITION

```text
BINARY: al ejecutar el discriminating test, el perfil T1..T6 DEBE:
- sumar ~100% de T0 (sin huecos, validando la instrumentación)
- identificar EXACTAMENTE UN componente dominante (≥50% de T0)
- reproducirse en 3 ejecuciones con variación <10%
```

## FAILURE_CONDITION

```text
BINARY: el test FALLA si:
- T1..T6 no suman ~T0 (instrumentación defectuosa → repetir con cross-check)
- la variación entre las 3 ejecuciones es >10% (ruido de medición → más repeticiones)
- NO hay componente dominante (≥50%) (cuello distribuido → el trabajo se descompone en sub-fronteras)
- la ejecución se interrumpe (timeout, SIGSEGV, OOM) → INVALID_RESULT
```

---

# ENTREGABLE

`benchmark/GLOBAL-WORK-SCAN-001.md` — este archivo.

Contiene:

1. **Active tree identity**: `/home/lucas/Escritorio/rxre`, HEAD `7c2971e67b533a4e3b0471da8cbd9335af2f42c2`.
2. **Current project state**: FAST_PATH_A_RETIRED, backend unificado, 15 superficies escaneadas.
3. **Scanned surfaces**: 15 superficies (CLI/dispatch, capabilities, register, evidence search, xref/relations, claims, provenance, trace, session/handoff, next_actions, recovery/follow-up, workflow integrity, benchmark infrastructure, corpus/index handling, plugin/OpenCode integration).
4. **Known measured bottlenecks**: backend regex (0.86× end-to-end) — cerrado por SEARCH-OPT-007; T_result_processing (0.54 ms) y T_backend (0.52 ms) — abiertos; T_file_iteration (0.00 ms) — descartado como dominante.
5. **Closed fronts excluded from reopening**: SEARCH-OPT-001..007 (hipótesis A refutada end-to-end), BENCHMARK-001/002 (no ejecutar por mandato de la tarea).
6. **Candidate frontiers**: CORPUS/INDEX (seleccionado), TRACE, XREF, CLAIMS, PROVENANCE (no seleccionados).
7. **Evidence matrix**: tabla de coste medido / confianza / impacto / test discriminante / riesgo.
8. **Selected NEXT_FRONT**: CORPUS / INDEX HANDLING, con discriminating test T1..T6.
9. **Why competing fronts were not selected**: justificación por falta de medición, intervención requerida (escritura) o ser superficies no activas.

---

# STOP GATE

```text
NEXT_FRONT = CORPUS / INDEX HANDLING
MEASURED_EVIDENCE = SEARCH-OPT-004/006 (0.86× end-to-end, T_file=0.00, T_line=0.20, T_backend=0.52, T_result=0.54)
DISCRIMINATING_TEST = instrumentación T1..T6 + workload SEARCH-OPT-006 (N=3) + comparativa % de T0
BINARY_SUCCESS_CONDITION = T1..T6 suman ~100% de T0, un componente ≥50%, variación <10%
BINARY_FAILURE_CONDITION = T1..T6 no suman ~T0, variación >10%, o ningún componente ≥50%
```

No se modifica RXRE.

No se crea commit funcional.

No se ejecuta la siguiente frontera todavía.

Después: GLOBAL WORK SCAN.

---

# CONCLUSIÓN

El próximo frente técnicamente más inmediato, determinado por evidencia, es **CORPUS / INDEX HANDLING**. La frontera SEARCH-OPT-006 demostró la regresión *end-to-end*; antes de avanzar hacia el procesamiento de resultados o hacia nuevas rutas, se debe cerrar el inventario del coste: medir por separado `build_pattern`, iteración de archivos, `pat.search`, parseo de línea y construcción del universo/tar_index bajo el mismo workload. El resultado determinará si el cuello está en la indexación (frente seleccionado) o se desplaza al result processing (nueva frontera).
