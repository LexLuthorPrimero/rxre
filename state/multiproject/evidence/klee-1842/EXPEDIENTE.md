# EXPEDIENTE — klee/klee#1842 + PR #1847

## Alcance
- Reproducción de SIGFPE en KLEE (IntrinsicCleaner, reescritura de `llvm.load.relative`) con offsets `i1`/`i2` (divisor truncado a 0).
- Fix: división en i32/wider en `IntrinsicCleaner.cpp::runOnBasicBlock` (commit fix/load-relative-narrow-offset @ 978c048, basado en master 6ba3a66).
- PR #1847: https://github.com/klee/klee/pull/1847 (base master, fork LexLuthorPrimero/klee autorizado).

## Evidencia (hashes en SEALED_PREDICTION.json)
- `subject.ll`, `harness.c`, `repro-host.bc` del reproducer (recompilados con LLVM 18.1.8, host triple `x86_64-redhat-linux-gnu`).
- Logs pre/post-fix: disponibles en `/home/lucas/eq-scratch/klee-repro/` (out-* dirs).
- Entorno: LLVM 18.1.8 (clang/llvm-as/opt/llvm-link), z3 5.3.1 sin STP, KLEE build RelWithDebInfo.
- Verificación pre/post: pre-fix SIGFPE (rc=136, señal 8) reproduces; post-fix no SIGFPE (29 instrucciones, 2 tests).
- Control i1/i16/i64/i16-symbolic documenta el alcance: OOB preexistente con input simbólica enmascarada — RESIDUAL, no corregido, declarado.

## Verificación independiente ciega (en curso — este estado)
- Verificador: subagente fresco en sesión hija; inputs: clone klee (rama fix/load-relative-narrow-offset, 2 commits: 6ba3a66, 978c048) y /home/lucas/eq-scratch/klee-repro (reproducer cegado).
- Restricción: NO puede leer /home/lucas/Escritorio/rxre en absoluto.
- Debe reconstruir y ejecutar ambos commits, capturar exit codes/señales/salidas y reportar diferencia de comportamiento.
- El sello SEALED_PREDICTION.json fue creado antes de lanzar el verificador (campo sealed_utc dentro del JSON).
- Veredicto pendiente: se registrará al retorno del verificador, junto con auditoría de sus accesos por rutas (log de la sesión hija).

## Estado técnico provisional (antes del veredicto ciego)
- Fix: validado con herramienta vanilla en este host (pre/post).
- Verificación por terceros: NOT_EXECUTED (verificación independiente aún en curso; 1 host, 1 UID, LLVM 18).
- Estado upstream: abierto (PR #1847).

## ESTADO ACTUALIZADO — Verificación ciega completada (2026-11-14T17:2xZ)

Veredicto: **SEALED_CONSISTENT / TESTED_ONLY** (evidencia: `VERDICT.json`).

- Reconstruction independiente en sesión hija: dos builds frescos desde git (pre-fix `6ba3a66` y fix `978c048`); sin leer `/home/lucas/Escritorio/rxre`; sin leer artefactos de ejecuciones previas.
- Pre-fix (6ba3a66): **SIGFPE (exit 136)** en `APInt::udiv` durante la evaluación de `udiv i2 %offset, 0`; `assembly.ll` confirma `%load.relative.index = udiv i2 %offset, 0`.
- Post-fix (978c048): sin SIGFPE. `assembly.ll`: `udiv i32 %load.relative.offset.ext, 4`. Con flags por defecto, aborta en `IndependentSolver::computeInitialValues` (assert "should satisfy the equation") tras reportar `memory error: out of bound pointer`. Con `--use-independent-solver=false`: exit 0, 2 tests generados (`completed paths = 1`, `partially completed paths = 1`, `total instructions = 29`).
- Auditoría de rutas del verificador: dentro de scope declarado; rxre NO.
- El sello fue creado antes del verificador (`seal_utc < verifier_start 2026-11-14T17:18:34Z`).

## LIMITACIONES (explícitas)
- 1 host, 1 UID, LLVM 18.1.8 + z3 5.3.1.
- El defecto residual (`out of bound pointer` + assert del independent solver) persiste post-fix; es un fallo **distinto** del #1842 y no está arreglado.
- La verificación proviene de una sesión hija fresca (miscelánea epistemológica entre investigador y verificador), no de un tercero humano.
- Estado epistémico máximo alcanzable aquí: TESTED_ONLY + SEALED_CONSISTENT. Nada de PROVEN.
- PR #1847 abierto; en revisión de mantenedores.
