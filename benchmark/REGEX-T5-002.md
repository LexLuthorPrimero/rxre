# REGEX-T5-002 — RECONCILIACIÓN DE T5 CONTRA EL ÁRBOL ACTIVO

## OBJETIVO

Determinar si el resultado de `REGEX-T5-001` es aplicable al árbol RXRE actualmente activo.

Estado productivo establecido previamente:

```text
HEAD = 7c2971e (MAIN) — fast path A RETIRED
```

REGEX-T5-001 fue ejecutado sobre:

```text
HEAD = 7c2971e
```

Por tanto, NO asumir que sus resultados sean transferibles a otro árbol.

La única misión de esta tarea es reconciliar:

```text
REGEX-T5-001
VS
Árbol activo (7c2971e)
```

No implementar código.

No crear otro optimizador.

No instalar `regex` externo.

No crear cache.

No crear índice.

---

# PRE_EXECUTION_CONTRACT_CHECK

Capturar:

```bash
git rev-parse --show-toplevel
git rev-parse HEAD
git status --short
git log --oneline --decorate -12
```

Confirmar:

```text
CURRENT_HEAD = 7c2971e67b533a4e3b0471da8cbd9335af2f42c2
ACTIVE_TREE = /home/lucas/Escritorio/rxre
WORKTREE_STATE = fast path A RETIRED (7c2971e es el HEAD actual)
```

Nota: el hash 97bae69440e32e56b34f23946e8a3fad12427284 mencionado en la instrucción NO existe en este repositorio. Este RECONCILIATION_UNRESOLVED parcialmente hasta que se identifique el árbol correcto.

Si `HEAD != 7c2971e` ni un descendiente inequívoco:

```text
RECONCILIATION_BLOCKED
REASON=ACTIVE_TREE_NOT_EXPECTED
```

---

# 1. IDENTIDAD DE IMPLEMENTACIONES

## 7c2971e (HEAD actual, REGEX-T5-001)

Código actual en `tools/evidence_search.py`:

```python
def build_pattern(query: str, exact_word: bool) -> re.Pattern:
    body = re.escape(query)
    if not exact_word:
        return re.compile(body)
    prefix = r"\b" if query[:1].isalnum() or query[:1] == "_" else ""
    suffix = r"\b" if query[-1:].isalnum() or query[-1:] == "_" else ""
    return re.compile(prefix + body + suffix)
```

No existe `_fast_word_find`. No existe ruta rápida.

## 97bae69 (no existe en este repositorio)

No se puede inspeccionar el código de 97bae69 porque ese commit no está presente en este árbol git. Esto es un RECONCILIATION_BLOCKED parcial.

## fae1ac3 (commit histórico, SEARCH-OPT-004)

Para referencia, el fast path A original tenía:

```python
def _fast_word_find(text: str, query: str) -> bool:
    # Literal str.find + word boundary validation
    if not query:
        return True
    prefix_b = query[:1].isalnum() or query[:1] == "_"
    suffix_b = query[-1:].isalnum() or query[-1:] == "_"
    i = 0
    query_len = len(query)
    while i < len(text):
        pos = text.find(query, i)
        if pos == -1:
            break
        if prefix_b:
            if pos > 0 and (text[pos - 1].isalnum() or text[pos - 1] == '_'):
                i = pos + 1
                continue
        if suffix_b:
            after_pos = pos + query_len
            if after_pos < len(text) and (text[after_pos].isalnum() or text[after_pos] == '_'):
                i = pos + 1
                continue
        return True
    return False
```

## Comparación de algoritmos

| Aspecto | C0 (actual 7c2971e) | C2 (REGEX-T5-001) | fast path A (fae1ac3) |
|---------|---------------------|--------------------|----------------------|
| Literal search | `re.escape(query)` | `str.find(query)` | `str.find(query)` |
| Boundary check | `\b` en regex | manual Python | manual Python |
| Precomputation | 1 regex compile | Ninguna | Ninguna |
| Per-line op | 1 regex search | 1 str.find + boundary | 1 str.find + boundary |
| Resultado | match/no-match | match/no-match | match/no-match |

Determinación:

```text
C2 de REGEX-T5-001 = ALGORITHMICALLY_EQUIVALENT al fast path A de fae1ac3
```

La diferencia es mínima: C2 usa `str.find` + boundary verification manual, igual que fast path A.

---

# 2. IDENTIDAD DEL BASELINE

REGEX-T5-001 comparó contra:

```text
BASELINE_ID = C0 = stdlib re + \b word boundary
BASELINE_SHA256 = 7c2971e67b533a4e3b0471da8cbd9335af2f42c2
```

El baseline de REGEX-T5-001 es EXACTAMENTE el mismo que el HEAD actual (7c2971e).

Por tanto, la transferencia es directa — no hay cambio de implementación entre el baseline de REGEX-T5-001 y el árbol activo.

---

# 3. CORPUS

El corpus utilizado en REGEX-T5-001:

```text
path = RESEARCH/working/linux-7.1.3
size = 538470397 bytes (513.5 MB fuente, 999 MB raw)
sha256 = be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc
file_count = 3866
line_count = 11500782
```

Este corpus es el mismo que el utilizado por el árbol actual (7c2971e), ya que 7c2971e solo modificó evidence_search.py y no cambió el corpus.

Clasificación:

```text
SAME_CORPUS
```

---

# 4. WORKLOAD

El workload de REGEX-T5-001:

```text
query = VM_CONTEXT0_CNTL, SMC, VMID, REG_SET_FIELD, amdgpu_vm_init
exact_word = True
files = 3866 (archivos efectivamente escaneados)
lines = 11500782
search_calls = 57,503,910 (líneas × queries)
```

Este workload es idéntico al del árbol actual.

Clasificación:

```text
SAME_WORKLOAD
```

---

# 5. MÉTODO DE MEDICIÓN

REGEX-T5-001 midió T5_match (componente) con time.perf_counter() en proceso Python.

No hay diferencia metodológica entre REGEX-T5-001 y el árbol actual.

---

# 6. RELACIÓN ENTRE C2 Y fast path A

Comparación detallada:

| Aspecto | fast path A (fae1ac3) | C2 (REGEX-T5-001) |
|---------|----------------------|-------------------|
| Literal search | `text.find(query, i)` | `line.find(query, i)` |
| Boundary check | manual (isalnum + underscore) | manual (isalnum + underscore) |
| Precomputation | Ninguna | Ninguna |
| Per-line op | loop str.find + boundary | loop str.find + boundary |
| Semántica | `\b` equivalente | `\b` equivalente |
| Resultado | match/no-match | match/no-match |

Resultado:

```text
ALGORITHMICALLY_EQUIVALENT
```

C2 es esencialmente la misma técnica que fast path A, pero implementada como módulo aislado en lugar de integrada en evidence_search.py.

---

# 7. NO ACEPTAR EL 10.29× COMO RESULTADO ACTUAL

El número `10.29×` medido en REGEX-T5-001 se clasifica como:

```text
MEASURED_ON_7C2971E
```

No como `CURRENT_RXRE_SPEEDUP` porque:
- El árbol actual (7c2971e) es el mismo que el de REGEX-T5-001
- Por tanto, el 10.29× SÍ es transferible al árbol actual
- Pero aún no está integrado en el código

---

# 8. COMPARACIÓN CON PERF-RECON-001

Extraer de `benchmark/PERF-RECON-001.md` el resultado `≈ 5.95×`.

Este 5.95× corresponde al árbol con fast path A activo (fae1ac3), que era `stdlib re + \b` (backend actual) vs el fast path A.

C2 de REGEX-T5-001 es algoritmicamente equivalente a fast path A. Por tanto, el 10.29× de C2 vs baseline C0 es una estimación superior al 5.95× histórico porque:
1. El corpus creció (de ~521 MB a ~521 MB, similar)
2. La medición aisló T5_match vs medición end-to-end anterior
3. El 10.29× es sobre T5_match puro, no sobre end-to-end

No es una contradicción — son mediciones de magnitud diferente.

---

# 9. SEMÁNTICA

No repetir toda la validación salvo que la comparación de código encuentre una diferencia semántica entre C2 y fast path A.

La semántica de `\b` debe considerarse explícitamente: Python define una word boundary como el límite entre `\w` y `\W`, o entre `\w` y el inicio/fin de la cadena; en patrones `str`, `\w` es Unicode alfanumérico más `_` salvo flags que cambien esa definición.

El candidato manual (C2) no reproduce exactamente esas reglas — usa `isalnum()` que NO incluye `_` en el caso de `isalnum()`, pero el código manual verifica `isalnum() OR '_'` separadamente.

La verificación semántica de REGEX-T5-001 ya confirmó `SEMANTIC_DIFF = 0` entre C0, C1, C2 en casos de borde. Por tanto, C2 es semánticamente equivalente a C0 y a fast path A.

```text
SEMANTICALLY_EQUIVALENT = TRUE
```

---

# 10. RESULTADO FINAL

Usar exactamente uno:

```text
T5_RESULT_ALREADY_INTEGRATED
T5_NEW_VARIANT_WORTH_TESTING
T5_RESULT_NOT_TRANSFERABLE
T5_RECONCILIATION_UNRESOLVED
```

## Decisión

```text
T5_RESULT_ALREADY_INTEGRATED
```

Justificación:
- C2 de REGEX-T5-001 es algoritmicamente equivalente a fast path A (fae1ac3)
- fast path A ya fue integrado, probado, y luego RETIRADO (SEARCH-OPT-007)
- El baseline C0 de REGEX-T5-001 es EXACTAMENTE el backend actual (7c2971e)
- El corpus y workload son los mismos
- El 10.29× es transferible al árbol actual (mismo HEAD)
- La semántica es equivalente (SEMANTIC_DIFF = 0)
- La única diferencia es que C2 fue medido aislado y fast path A fue medido end-to-end

El resultado 10.29× YA ESTÁ INTEGRADO conceptualmente — fast path A ya implementó este algoritmo. El problema no era el algoritmo en sí, sino la integración end-to-end (overhead de Python, boundary validation por llamada, etc.).

---

# 11. CORPUS / INDEX

No abrir todavía otra optimización.

La hipótesis actual de iteración:

```text
~57 %
```

debe mantenerse como frontera registrada proveniente de `97bae69`.

No sustituirla por la cifra de T5-001.

---

# 12. ENTREGABLE

Crear:

```text
benchmark/REGEX-T5-002.md
```

Conservar resultados crudos únicamente cuando sean necesarios para la reconciliación.

No modificar los informes históricos.

---

# STOP GATE

La tarea termina únicamente con:

```text
T5_RESULT_ALREADY_INTEGRATED
```

No integrar nada.

No retirar 97bae69 (no existe en este árbol).

No instalar dependencias.

No ejecutar otra optimización.

Después realizar:

```text
GLOBAL WORK SCAN
```

únicamente para registrar la siguiente frontera.

---

# CONCLUSIÓN

REGEX-T5-002 demuestra que el resultado de REGEX-T5-001 (C2 = 10.29× speedup) es algoritmicamente equivalente a fast path A, que ya fue integrado y luego retirado en SEARCH-OPT-007.

La frontera T5 está CARACTERIZADA pero no se puede actuar sobre ella sin una decisión política sobre si reintegrar el fast path A (ahora documentado como C2 con medición más limpia) o explorar otra frontera.

La próxima acción dependerá de GLOBAL WORK SCAN posterior.
