# EXPEDIENTE — klee/klee#1841 + PR #1848

## Alcance
- Falso `ASSERTION FAIL` con `--optimize-array=index` (y `=all`) en un programa cuyas aserciones se cumplen para todo input.
- Root cause: `ExprOptimizer::computeIndexes` en `lib/Expr/ArrayExprOptimizer.cpp` usaba **cualquier** factor constante en el predicado como stride de enumeración de índices de un array constante. Un constante que multiplica un **valor leído** (no el índice) restringe la divisibilidad del array leído, no del índice → índices válidos quedan fuera, ramas factibles marcadas infactibles.
- Fix: eliminar el override `getMul()` para stride; el stride queda derivado exclusivamente de `idxt_v.getWidth() / arr->range`.
- Rama: `fix/array-optimizer-mul-stride @ 34fb8ad` (base master 6ba3a66). PR #1848: https://github.com/klee/klee/pull/1848

## Evidencia
- Entorno: LLVM 18.1.8 (clang/llvm-link), z3 (ENABLE_SOLVER_Z3=ON), KLEE RelWithDebInfo, **Asserts: ON**.
- Reproducer del issue (`subject.c`/`harness.c`/`repro.bc` en `/home/lucas/eq-scratch/repro-1841/`): pre-fix `ERROR: harness.c:15: ASSERTION FAIL: index!=2u` (1 completed path); post-fix: `completed paths = 2`, sin `ASSERTION FAIL`. Igual con `--optimize-array=all` y con `--optimize-array=value`.
- Test de regresión añadido: `test/ArrayOpt/test_mul_loaded_stride.c` (RUN líneas + FileCheck; verificado con runner manual estilo lit en este host).
- Control negativo: con el binario pre-patch (stash + rebuild) el mismo log de fallo (`IndependentSolver` assert) aparece; confirmado que `test_expr_arbitrary.c` falla idéntico en master **y** con el patch → **preexistente, no regresado**.
- Suite `test/ArrayOpt`: 21/22 PASS. Único fallo: `test_expr_arbitrary.c` (assert en `IndependentSolver::computeInitialValues` tras `out of bound pointer` en línea 26) — preexistente, no relacionado con el optimizer (confirmado pre/post patch, mismo comportamiento).
- `test_expr_mul.c` (cobertura preexistente de OPT_I): PASS.

## Limitaciones (explícitas)
- 1 host, 1 UID, LLVM 18.1.8 + z3; runner manual estilo lit (lit no instalado en este host); CI oficial de KLEE corre con otras configs (Asserts OFF, STP disponible).
- Verificación cegada **no** ejecutada para este fix (solo validación directa pre/post en este host).
- Estado epistémico máximo: TESTED_ONLY. Nada de PROVEN.
- El defecto del independent solver (assert tras out-of-bound pointer) es distinto y sigue abierto; es el señalado en #1842 como RESIDUAL.
- PR #1848 abierto; pendiente de review de mantenedores.

## Próximos pasos
- Vigilar CI/review de #1848 (y #1847, miasm #1591/#1592/#1593, angr #7788, REA 20, rizin 5 — rizin en silencio por dictado).
- Verificación ciega opcional para #1841 si el propietario lo pide (contrasesión hija, como se hizo para #1842).
