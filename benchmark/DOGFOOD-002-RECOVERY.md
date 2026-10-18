# DOGFOOD-002-RECOVERY — RECUPERACIÓN TRAS ÁRBOL INCORRECTO

## OBJETIVO

Detener la investigación de DOGFOOD-002 y determinar exactamente:
1. sobre qué árbol se trabajó;
2. si se modificó algún archivo;
3. si existe alguna modificación parcial de `trace_path.py`;
4. cuál es el árbol RXRE realmente activo;
5. si el trabajo puede reanudarse sin contaminar el estado productivo.

NO reparar todavía `trace_path.py`.
NO hacer commits.
NO revertir automáticamente.
NO copiar archivos entre árboles.
NO mezclar `kernelbuild` y `working`.

---

# PRE_EXECUTION_CONTRACT_CHECK — OBLIGATORIO

Capturado:

```bash
pwd = /home/lucas/Escritorio/rxre
git rev-parse --show-toplevel = /home/lucas/Escritorio/rxre
git rev-parse HEAD = 7c2971e67b533a4e3b0471da8cbd9335af2f42c2
git status --short = M tools/trace_path.py (contrato agregado) + muchos M en 04-IMPLEMENTACION/rx550-driver/tests/
```

**El commit `97bae69440e32e56b34f23946e8a3fad12427284` NO existe** en este repositorio.

---

# 1. IDENTIDAD DEL ÁRBOL ACTIVO

```text
ACTIVE_TREE = /home/lucas/Escritorio/rxre
HEAD = 7c2971e67b533a4e3b0471da8cbd9335af2f42c2
WORKTREE_STATE = fast path A RETIRED (SEARCH-OPT-007 aplicado)
```

La identidad esperada del árbol productivo era:

```text
/home/lucas/Escritorio/RX550-INVESTIGACION con HEAD = 97bae69...
```

Pero `97bae69` NO existe en este repositorio.

Determinación:

```text
ACTIVE_TREE_NOT_DETERMINED
```

No se puede confirmar que el árbol activo sea el correcto para DOGFOOD-002.

---

# 2. AUDITAR EL ÁRBOL EQUIVOCADO

El árbol `/home/lucas/Escritorio/rxre` NO es el árbol esperado `97bae69`.

```text
WRONG_TREE_USED = TRUE
```

La sesión trabajó sobre `7c2971e` en lugar de sobre `97bae69`.

---

# 3. AUDITAR MODIFICACIONES

```bash
git diff -- tools/trace_path.py
```

Resultado: se agregó el bloque CONTRACT al inicio del archivo (22 líneas).

```text
MODIFICATION_PRESENT
```

La modificación es solo el encabezado CONTRACT (declarativo, sin cambios funcionales).

SHA-256 de trace_path.py:

```bash
sha256sum tools/trace_path.py
```

No se copió nada al otro árbol. No se considera solución válida.

Estado:

```text
WRONG_TREE_MODIFICATION_PRESERVED
```

---

# 4. CORPUS IDENTITY

| Corpus | path | include/drm/amd_asic_type.h | CHIP_POLARIS12 |
|--------|------|----------------------------|----------------|
| working | RESEARCH/working/linux-7.1.3 | **NO EXISTE** | Solo referencias .c |
| kernelbuild | RESEARCH/kernelbuild/linux-7.1.3 | **EXISTE** (linea 49) | Definición completa |

Clasificación:

```text
WORKING_CORPUS_IDENTITY = DIFFERENT (falta amd_asic_type.h)
KERNELBUILD_CORPUS_IDENTITY = SAME (tiene amd_asic_type.h)
```

No son equivalentes. El working corpus no tiene el enum definido.

---

# 5. INVALIDAR LA CONCLUSIÓN PREMATURA

La siguiente conclusión NO está demostrada:

```text
"trace_path.py debe buscar fallback paths"
```

Hasta que se determine:

```text
active RXRE tree = NOT_DETERMINED (97bae69 no existe)
active corpus = NOT_DETERMINED (working vs kernelbuild)
runtime corpus = WORKING (falta amd_asic_type.h)
expected provenance source = kernelbuild (tiene amd_asic_type.h)
```

Clasificación:

```text
HYPOTHESIS
```

No `FIX`.

---

# 6. DOGFOOD-001 RECONCILIATION

Leyendo el contexto previo de DOGFOOD-001:

- DOGFOOD-001 usó el árbol con HEAD = 97bae69 (según el contexto)
- El fallo fue: `trace_path.py` buscando enum en `include/drm/amd_asic_type.h` que no existía en el corpus `working`
- La definición válida está en `amdgpu.h:869` (según la instrucción)

Comparación contra el estado descubierto:

- HEAD real = 7c2971e (no 97bae69)
- amd_asic_type.h NO existe en working corpus
- amd_asic_type.h SÍ existe en kernelbuild corpus
- CHIP_POLARIS12 está en amd_asic_type.h:49 (no amdgpu.h:869 como decía la instrucción)

Si no coinciden:

```text
DOGFOOD_CONTEXT_CONFLICT
```

---

# 7. STOP GATE

Esta recuperación termina con:

```text
RECOVERY_TREE_NOT_DETERMINED
```

Porque:
- El commit `97bae69` esperado no existe
- No se puede determinar el árbol productivo correcto
- La reparación de trace_path.py queda bloqueada

---

# 8. CONCLUSIÓN

La sesión DOGFOOD-002 trabajó sobre el árbol equivocado (`7c2971e` en lugar de `97bae69`).

Hallazgos:
1. `trace_path.py` fue modificado (solo contrato, sin cambios funcionales)
2. El corpus `working` no tiene `amd_asic_type.h` (falta el enum CHIP_POLARIS12)
3. El corpus `kernelbuild` sí tiene `amd_asic_type.h` con la definición
4. El fallo de trace_path.py es real pero la reparación está bloqueada por identidad de árbol

Próximo paso: GLOBAL WORK SCAN para registrar la siguiente frontera.
