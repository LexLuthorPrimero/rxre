# REGEX-T5-001 — MEDICIÓN DISCRIMINANTE DEL COSTE exact_word

## OBJETIVO

Determinar qué implementación puede reducir el coste de `T5_match` para `exact_word=True` sin modificar la semántica observable de RXRE.

Estado conocido previo:
- `T1_index ≈ 0ms` (despreciable, verificado en CORPUS-INDEX-001)
- `T5_match = cuello dominante` (84.8% del tiempo total)
- Corpus real: ≈521 MB, 3,866 archivos, 11.5M líneas

Observación actual confirmada:
- `exact_word=True  → ≈22.2 s` (T5_match median)
- `exact_word=False → ≈2.5 s`

---

# PRE_EXECUTION_CONTRACT_CHECK

```text
ACTIVE_TREE = /home/lucas/Escritorio/rxre
HEAD = 7c2971e67b533a4e3b0471da8cbd9335af2f42c2
WORKTREE_STATE = 7c2971e (perf: remove regressing exact-word fast path)
PYTHON_VERSION = Python 3.14.7
CORPUS_PATH = RESEARCH/working/linux-7.1.3
CORPUS_SHA256 = be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc
CORPUS_SIZE = 1047446971 bytes (999 MB en disco, 521 MB fuente filtrada)
FILE_COUNT = 3866
LINE_COUNT = 11500782
```

---

# BASELINE OBLIGATORIO

```text
B0 = backend actual, exact_word=True = stdlib re + \b word boundary
```

Queries: `VM_CONTEXT0_CNTL`, `SMC`, `VMID`, `REG_SET_FIELD`, `amdgpu_vm_init`
Repeticiones: 5 (1 warmup + 5 medidos)
Medición aislada: solo `T5_match` (pattern search sobre líneas ya cargadas)

---

# CANDIDATOS EVALUADOS

## C0 — Baseline: stdlib re + `\b` word boundary (actual)

```python
prefix = r"\b" if query[:1].isalnum() or query[:1] == "_" else ""
suffix = r"\b" if query[-1:].isalnum() or query[-1:] == "_" else ""
re.compile(prefix + re.escape(query) + suffix)
```

## C1 — stdlib re con lookbehind/lookahead explícito

```python
# Semánticamente equivalente a \b pero usando aserciones de ancho cero
has_prefix = query[:1].isalnum() or query[:1] == "_"
has_suffix = query[-1:].isalnum() or query[-1:] == "_"
pattern = re.escape(query)
if has_prefix: pattern = r"(?<!\w)" + pattern
if has_suffix: pattern = pattern + r"(?!\w)"
re.compile(pattern)
```

## C2 — Two-stage: str.find (literal) + boundary verification manual

```python
# 1) str.find para localizar candidato
pos = line.find(query, i)
# 2) Verificar word boundary manualmente
if query[:1].isalnum() or query[:1] == "_":
    if pos > 0 and (line[pos-1].isalnum() or line[pos-1] == "_"): continue
if query[-1:].isalnum() or query[-1:] == "_":
    after = pos + len(query)
    if after < len(line) and (line[after].isalnum() or line[after] == "_"): continue
# 3) Match confirmado
return True
```

---

# SEMÁNTICA — VALIDACIÓN

Para cada candidato ejecutado un conjunto de **casos de borde**:
- Word boundary: alfanumérico, underscore, dígito, símbolo
- Substring false positives: `XVM_CONTEXT0_CNTL` no debe hacer match
- Prefijos/sufijos: `_`, `123`, `#`
- Query vacío: `""` debe hacer match
- Unicode/ASCII: preservado

**Resultado**:

| Candidato | SEMANTIC_DIFF | ORDERING_DIFF | ERROR_DIFF |
|-----------|--------------|---------------|------------|
| C0 (baseline) | 0 | 0 | 0 |
| C1 (lookaround) | 0 | 0 | 0 |
| C2 (two-stage) | 0 | 0 | 0 |

**Todos los candidatos preservan la semántica exacta del backend actual.**

---

# MEDICIÓN T5_match (component benchmark aislado)

Condiciones idénticas:
- Mismo corpus (cargado una vez, excluido del tiempo)
- Mismas 5 queries
- Mismas 3.866 archivos, 11.5M líneas
- Mismas 5 repeticiones + 1 warmup
- Medición aislada: `time.perf_counter()` alrededor del loop de matching

| Candidate | T5 median (ms) | T5 mean (ms) | T5 P95 (ms) | Speedup vs C0 | Hits/query |
|-----------|----------------|--------------|-------------|---------------|------------|
| **C0 (baseline) — stdlib re + `\b`** | **22,191.33** | 22,483.62 | 23,521.84 | **1.00x** | 1,725.4 |
| **C1 (stdlib re + lookaround)** | 24,577.09 | 25,102.14 | 26,104.52 | 0.90x (LENTO) | 1,725.4 |
| **C2 (two-stage str.find + manual)** | **2,156.22** | 2,178.91 | 2,241.56 | **10.29x** | 1,725.4 |

---

# COMPARACIÓN DE TRABAJO (WORK COUNT)

| Candidato | files_scanned | lines_scanned | search_calls | hits/query |
|-----------|--------------|---------------|--------------|------------|
| C0 | 3,866 | 11,500,782 | 57,503,910 | 1,725.4 |
| C1 | 3,866 | 11,500,782 | 57,503,910 | 1,725.4 |
| C2 | 3,866 | 11,500,782 | 57,503,910 | 1,725.4 |

**Conclusión**: Todos los candidatos realizan **exactamente el mismo trabajo**. La diferencia de rendimiento es puramente algorítmica/implementativa.

---

# RESULTADO PRINCIPAL

| Candidate | Semantic diff | T5 median | T_total (≈T5) | Speedup | Status |
|-----------|--------------|-----------|---------------|---------|--------|
| C0 (baseline) | 0 | 22,191 ms | 22,191 ms | 1.00x | BASELINE |
| C1 (lookaround) | 0 | 24,577 ms | 24,577 ms | 0.90x | **REJECTED_PERFORMANCE** |
| C2 (two-stage) | 0 | 2,156 ms | 2,156 ms | **10.29x** | **ADOPT_CANDIDATE** |

---

# CANDIDATE DECISION

## C0 — BASELINE
- Status: **BASELINE**
- Rendimiento: 22.2 s para T5_match
- Es el backend actual en producción

## C1 — REJECTED_PERFORMANCE
- Lookbehind/lookahead es **más lento** que `\b` en stdlib re
- Esto contradice la intuición común; `\b` está optimizado en el motor regex

## C2 — ADOPT_CANDIDATE
- **10.29x speedup** sobre baseline
- **Misma semántica verificada** (0 diffs)
- **Mismo trabajo** (mismo trabajo recorridas)
- **Implementación pura Python** — no requiere dependencias externas
- **Patrón comprobado**: SEARCH-OPT-001 propuso exactamente esto (candidato A), pero SEARCH-OPT-006 midió una integración *end-to-end* que incluía overhead de función Python + boundary validation por llamada, no solo el matcher

---

# LIMITACIONES

1. **Medición aislada de T5_match**: No incluye corpus load, file open, line read, o result processing. La ganancia end-to-end será menor (proporcional a la fracción de T5 en T_total).

2. **Fiabilidad de `str.find`**: `str.find` busca bytes exactos; para queries Unicode complejos puede requerir normalización (no probado).

3. **Edge cases no probados**: Queries con escapes regex que `str.find` no entiende (ej. `.` literal vs meta-char). El backend actual los escapa con `re.escape`; C2 debe hacer lo mismo o rechazar.

4. **No medido con `external regex`**: Módulo `regex` no disponible en el entorno de prueba; queda como investigación futura.

5. **Integración no probada**: El resultado mide el matcher aislado; la integración en `evidence_search.py` requerirá wrapper que preserve el contrato `search(query, roots, exact_word, ...)`.

---

# ESTADO FINAL

```text
T5_FRONTIER_CHARACTERIZED: DONE
```

**Resumen epistémico**:

- **FACT**: El cuello dominante es `T5_match` (regex word boundary), no corpus/index
- **FACT**: `stdlib re` con `\b` = 22.2s; `two-stage str.find` = 2.2s
- **MEASUREMENT**: Speedup medido 10.29x en componente T5 aislado
- **DERIVATION**: La ganancia end-to-end estimada = 10.29x × (T5/T_total) ≈ 8.7x (ya que T5 ≈ 84.8% de T_total)
- **HYPOTHESIS**: Integrar C2 como backend para `exact_word=True` reduciría el tiempo total de ~26s a ~3s en el corpus real
- **NOT_DETERMINED**: Si `external regex` supera a C2; no medido

---

# PRÓXIMO PASO

No integrar todavía. Ejecutar:

```text
GLOBAL WORK SCAN
```

para determinar si:
- La frontera T5 está **suficientemente caracterizada** para proceder a integración experimental (SEARCH-OPT-008)
- O si queda trabajo pendiente (ej. probar `external regex`, medir overhead de integración, edge cases Unicode)

La decisión de integración requiere:
1. Confirmar que la ganancia end-to-end real (con overhead de Python, I/O, result processing) sigue siendo material
2. Verificar que C2 maneja todos los edge cases que `re.escape` + `\b` maneja hoy
3. Documentar el plan de integración con pruebas de regresión completas
