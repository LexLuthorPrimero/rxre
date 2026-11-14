# cap.equiv_check — verificación acotada de equivalencia semántica nativa

- **Problema que resuelve**: decidir si un candidato (C o binario) se comporta como el original binario para funciones escalares int→int, con veredicto honesto.
- **Veredictos**: PROVEN (z3/UNSAT, dominio completo en el modelo) | MISMATCH (contraejemplo + confirmación nativa) | TESTED_ONLY (corpus finito) | INCONCLUSIVE (no se sabe).
- **Implementación**: `tools/rxre/semantic/equiv_check.py` (CLI + API `check()`).
- **Pruebas**: `tools/rxre/tests/test_semantic_equiv_4972.py` — 7/7 PASS (2026-11-14).
- **Evidencia**: `state/multiproject/evidence/rea-4972/eq-*.json` + `EXPEDIENTE.md`.
- **Dependencias**: angr 10.0.5 (VEX lift), z3 5.3.1, gcc, ctypes (control concreto con fork-per-call).
- **Entrada**: binario original + símbolo (o `--orig-addr`), candidato C/binario, `--sig u64|i64`.
- **Salida**: JSON (hashes, versiones, capas, veredicto, contraejemplo, scope/limitaciones).
- **Madurez**: experimental-integrada en RXRE (testeada, sin wiring upstream).
- **Limitaciones**: ver EXPEDIENTE.md — modelo VEX, sin memoria/entorno, fork-per-call Linux.
- **Reutilización potencial**: REA #4972 (provider de equivalencia), validación de transformaciones en rizin (p.ej. lift→C), checks de angr decompiler (candidate vs original), oráculo independiente para harness R3.
- **Relación con capacidades existentes**: complementa `cap.ir_sim`/`cap.diff_harness` (diffinito parcial, no equivalencia), `cap.ghidra_decomp` (PARTIAL, sin veredicto). Ninguna capacidad existente cubría el veredicto PROVEN/MISMATCH.
