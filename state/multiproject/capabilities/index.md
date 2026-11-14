# RXRE — Mapa de capacidades verificadas (2026-11-14)

Método: exploración estructurada del árbol (`tools/rxre/`, 710 .py; 291 test_*.py recursivos). **No se re-ejecutaron las suites**; "testeado" = tests existentes. Madurez según evidencia, no según prosa del README.

## A. Implementado + testeado (productor real en host)

| ID | Capacidad | Ubicación | Entrada → Salida | Dependencias | Tests | Estado |
|---|---|---|---|---|---|---|
| cap.rizin_inspect | inspección binaria rizin (`rz-bin -Ij`) | `tools/rxre/backends/adapters/rz_inspect.py` | artefacto → JSON evidencia | rizin 0.7.4 | test_backends004, test_xrefs1635 | Implementado+testado |
| cap.r2_cfg | CFG/callgraph/dataflow JSON vía radare2 | `adapters/rz_cfg.py`, `rz_callgraph.py` | bins → CFG/callgraph | radare2 5.9.8 | test_dataflow, test_integration_cfg | Implementado+testado |
| cap.cs_disasm | desensamblado in-process | `adapters/cs_disasm.py` | bytes → mnemos | capstone 5.0.7 | test_disasm1634 | Implementado+testado |
| cap.cocci_search | búsqueda semántica en fuente | `adapters/cocci_search.py` | spatch | coccinelle 1.3.1 | test_adapter_provenance_fix_044 | Implementado |
| cap.ts_ast | AST de fuente (venv aislado) | `adapters/ts_ast.py` | C → árbol | tree-sitter (.venv/eco) | test_eco_ast001 | Implementado+testado |
| cap.ghidra_decomp | decompilación PARTIAL (no ET_REL) | `adapters/gh_decompile.py` | ELF → C pseudo | Ghidra 12.1.4 | test_decomp003 | Implementado+testado (PARTIAL) |
| cap.rz_functions/xrefs/container | inventarios rizin/r2 | `adapters/rz_*.py` | bins → JSON | rizin/radare2 | test_container1632 (⚠ zstd ausente), test_xrefs1635 | Implementado+testado |
| cap.umr_read / cap.mmr_read | lectura registros RX550 (root / ioctl sin priv.) | `adapters/umr_read.py`, `mmr_read.py` | mmGRBM_STATUS → 0x3028 | umr/ioctl | test_umr_hardware002 (root), test_mmio_adapter_012 | Implementado+testado |
| cap.verifier_bwrap | clean-room verificación (bwrap confinado) | `verifier/independent_verifier.py`, `sandbox.py`, `acceptance_policy.py`, `promotion.py` | paquete → dictamen | bwrap | test_independent_verifier, test_verifier_004, test_acceptance_policy | Implementado+testado |
| cap.ssa | SSA mínima (Cooper-Harvey-Kennedy) | `analysis/ssa.py` | grafo → SSA | — | test_ssa | Implementado |
| cap.ir_sim | IR mínima (subset MOV/ADD/SUB/CMP/JMP/JZ/CALL/RET/PHI) | `analysis/ir.py`, `analysis/dataflow.py` | IR → simulación | capstone | test_diff_harness, test_dataflow | Implementado+testado (acotado) |
| cap.diff_harness | diff IR vs capstone, verdict MATCH-acotado | `analysis/diff_harness.py` | bloques → veredicto | capstone | test_diff_harness | Implementado+testado |
| cap.cfg_coverage | métricas de cobertura CFG | `analysis/cfg_coverage.py` | aflj/agfj → % | rizin/radare2 | test_cfg_coverage | Implementado (medido sobre /usr/bin/ls) |
| cap.indirect_targets | resolución de saltos indirectos (SINGLE/FINITE/MAY/UNKNOWN) | `analysis/indirect_targets.py` | CFG → targets | capstone | test_m384_indirect_got | Implementado (acotado) |
| cap.m58_spirv | pipeline SPIR-V verif→dis→extr→sem | `polaris12/m58/m58_spirv_pipeline.py`, ROUTER producers | .spv → report | spirv-* | tests/test_m58_* (pytest) | Implementado+testado |
| cap.machine_cli | CLI `machine.py` (~29 handlers cableados) | `api/machine.py` | op:X → resultado+rc | backends | test_cli009, test_dispatch004 | Implementado+testado |
| cap.arquitectura_stack | andamiaje epistémico (ETER/TIERRA/AGUA/AIRE/ALMA/ROUTER/PUERTA/planos/schemas) | `arquitectura/*.py` | claims→evidence→grafo→puerta | sqlite | test_arquitectura_v3_* | Implementado+testado (scaffolding, NO análisis binario) |

## B. Instalado pero NO integrado/testeado

| ID | Capacidad | Estado real |
|---|---|---|
| cap.angr_re | angr 10.0.5 **importable**, `angr_m417.py`, `run_angr_real.py`, `e2e_integrated.py` | **Cero tests**; decision.json/registry dicen `NOT_DETERMINED` (obsoleto). Hueco demostrado. |
| cap.z3_formal | z3 5.3.1 importable | **Ningún uso** fuera de tests; `formal.check` = productor vacío en dispatch.py. Hueco demostrado. |

## C. Documentado-pero-no-implementado / stubs

- `runtime.trace`, `formal.check` (ADAPTERS vacíos en `backends/dispatch.py`).
- `op: case` (AI_QUICKSTART; no existe en machine.py); AI_QUICKSTART describe interfaz antigua (rc incorrecto).
- `decompiler/lifter.py` (3 funciones hardcodeadas); `test_decompiler.py` con fixture ausente.
- `test_mega_complete.py`, `test_remaining_partials.py` (API inexistente → muertos).
- `schemas.py::CASILLAS.falsification_test` (node-ids inexistentes).
- Dos stacks duplicados de los 9 elementos (`arquitectura/` vs `core/`).
- README: "24/26 adapters", "32 test files" → real: ~29 cableados; 280 test_*.py en tools/rxre/tests/.
- `verify/verify_evidence.py`, `verify_learning.py` (rotos); `swf_inspect.py` (parser incompleto).

## D. Reutilizables entre proyectos (demostradas o potenciales)

| Capacidad | Reutilización demostrada/potencial |
|---|---|
| cap.rizin_inspect / cap.cs_disasm / cap.ghidra_decomp | Cualquier binario/formato (rizin↔angr↔REA) |
| cap.verifier_bwrap | Verificación independiente aplicable a candidatos de Cualquier repo |
| cap.ir_sim / cap.diff_harness | Comparación IR-vs-binario; base de equiv_check (ver D abajo) |
| cap.indirect_targets / jump_tables | CFG de rizin; aplicables a lifting y a angr CFG |
| **cap.equiv_check** (NUEVA, este slice) | Equivalencia semántica binario↔binario; objetivo REA #4972; reutilizable para validar transformaciones rizin y diffs de compiler/angr |

## Detalle

Ver `capabilities/equiv_check.md` (nuevo), `evidence/`. El mapa base proviene de la exploración 2026-11-14; los estados deben reverificarse antes de citarlos como vigentes.
