# cap.thumb_literal_oracle — oráculo diferencial Thumb-2 (literal U=0/U=1)

- **Problema que resuelve**: detectar divergencias de decodificación en instrucciones LDR/LDRB (literal) entre un decodificador candidato y RXRE-capstone; el caso real fue miasm #1570.
- **Implementación**: `tools/rxre/analysis/thumb_literal_oracle.py`. Capstone vía `backends.adapters.cs_disasm` (decode en 4 ventanas de 1024 instrucciones — adapter limitado a 4000 instrucciones por llamada).
- **Entrada**: `--family {ldr_neg|ldrb_neg|ldr_pos|ldrb_pos} --candidate-python <python con miasm importable>`; `MIASM_CLONE=<path>` vía env.
- **Salida**: JSON {status, bytes_compared, bytes_matched, coverage_pct, disagreements[]}.
- **Pruebas**: `--family ldr_neg` (y las otras 3) comparando contra miasm `fix/armt-ldr-literal-neg`; resultado 4096/4096 en las 4 familias. Control negativo: contra `df358f7` (pre-fix) — 0/4096 en `ldr_neg` y `ldrb_neg`, 4096/4096 en las dos U=1; i.e., el oracle discrimina exactamente el caso denunciado.
- **Estado de madurez**: implementada + ejecutada + validada (RXRE). Reutilizada entre proyectos (0 aún).
- **Limitaciones**: comparación categorizada por base/disp/reg — no cubre casos con efecto write-back (ej. ldr literal U=0 con base writeback-flag es una clase distinta); coverage se ejecuta por ventana (4096 bytes); la herramienta del stub asume miasm como candidato (parametrizable por env var).
- **Reutilización potencial**: contrastar resultados de lifts angr/remill/binsec contra capstone (R program-count); harness para #1570 y futuros T2 U=0 issues; check de regresión post-patch.
- **Deps**: capstone 5.0.7, Python; miasm como candidato (`MIASM_CLONE`).

**Relación con RE-1634 (cs_disasm)**: el adaptercs en `tools/rxre/backends/adapters/cs_disasm.py` fue extendido a Thumb mode + operand handling ARM (REG/IMM/MEM); `test_disasm1634`: 36 checks 0 failures; `test_backends004` fail preexistente y sin cambios tras la extensión.
