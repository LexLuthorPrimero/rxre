# EXPEDIENTE — morluto/rea#4972 (verificación de equivalencia semántica nativa)

## Estado epistémico de este expediente
**PARTIAL**: prototipo vertical funcionando y testeado como capacidad RXRE; sin wiring upstream aún; PROVEN aquí = z3/UNSAT en el modelo explícito (VEX lift, SysV AMD64, un argumento entero, sin efectos de memoria ni entorno, sin UB). No es verificación general de binarios arbitrarios.

## Alcance acotado del slice
- Funciones **escalares de un argumento entero** (u64/i64), retorno entero en `rax`, SysV AMD64.
- Comparación semántica **binario ↔ binario** (ambos levantados a VEX por angr 10.0.5); candidato puede ser C (se compila con gcc -O2 -fPIC -shared).
- Capa simbólica: angr + z3 (UNSAT sobre todo el dominio ⇒ PROVEN; SAT ⇒ counterexample ⇒ MISMATCH).
- Capa concreta: ctypes con **fork-por-llamada** (un crash no tumba al verificador), comparación sobre corpus boundary+seed (64 casos). Se usa como control, nunca como prueba.
- Sin modelado de: memoria global, efectos laterales, entorno/ABI más allá del registro, FP, UB, llamadas externas. Funciones con esas propiedades **no las reclama este slice** (INCONCLUSIVE o TESTED_ONLY).

## Hechos verificados (2026-11-14)
- `tools/rxre/semantic/equiv_check.py` — implementación (CLI + API).
- `tools/rxre/tests/test_semantic_equiv_4972.py` — 7 tests, **7 passed** (pytest y `python3 -B` rc=0, RXRE run_tests.sh-compatible).
- Evidencia `state/multiproject/evidence/rea-4972/eq-*.json` (5 runs):
  - `eq-orig-vs-ok.json`: PROVEN (x*256 vs x<<8) — conc_ok=true
  - `eq-orig-vs-ok2.json`: PROVEN (x*256 vs x*128+x*128)
  - `eq-orig-vs-bad.json`: MISMATCH cex=0x22ae99ebbffeb47d (x*25) — counterexample confirmado contra ejecución nativa
  - `eq-br-vs-br.json`: PROVEN — función con rama (ITE-merged)
  - `eq-br-vs-bad.json`: MISMATCH cex=0x0 — contraejemplo mínimo
- Controles negativos cubiertos: candidato incorrecto de rama-única y de rama múltiple; skip_symbolic → TESTED_ONLY; orig ausente / C inválido → INCONCLUSIVE.
- Independencia: el veredicto simbólico (z3/UNSAT) no depende de la ejecución nativa; la ejecución nativa se usa solo como control. El test verifica el counterexample con ctypes directo, sin pasar por el módulo.

## Hashes (ejecución de evidencia, esta máquina)
- Fixtures (pinned en `fixtures/`): fuentes sha256 parcialmente listadas dentro de cada JSON (`hashes.cand_source`).
- El `.so` del original se compila al vuelo; su sha256 exacto (`hashes.orig`) depende del gcc del host (gcc 16.2.1 20260819) y **no es idéntico entre máquinas** — reverificar recompilando los fixtures, no por hash del binario.
- Entorno: python 3.14.8, angr 10.0.5, z3 5.3.1, gcc 16.2.1, capstone 5.0.7 (vía angr).

## Comandos
```
python3 -B tools/rxre/tests/test_semantic_equiv_4972.py   # rc=0 (7 passed)
python3 tools/rxre/semantic/equiv_check.py --orig ORIG --orig-func f --cand CAND.c [--out JSON]
```

## Limitaciones declaradas
1. PROVEN es sobre el modelo VEX lift, no sobre el ISA físico ni sobre el C fuente.
2. `counterexample_confirmed_native` fue `true` en ambos MISMATCH.
3. El mismatch cex puede no ser el mínimo (z3 devuelve un testigo arbitrario).
4. Sin wiring upstream en REA todavía: la issue pide provider contract + CLI/MCP; este slice entrega la verificación y su contrato de resultados, no la integración.
5. ctypes solo soporta funciones `uint64/int64(uint64/int64)`; otros ABIs → capa concreta no disponible (la simbólica y el veredicto lo reflejan).
6. fork-per-call asume Linux.

## Pendiente
- Wiring upstream REA (provider externo CLI/MCP, result contract PROVEN/MISMATCH/TESTED_ONLY/INCONCLUSIVE) — requiere decisión del propietario y sesión dedicada.
- Ampliar dominio: más argumentos, retornos múltiples, funciones con memoria global (mempred), funciones con llamadas.
- Pre-flight antiduplicados antes de cualquier PR (`gh pr list --search`).

## Estado upstream
- morluto/rea#4972: **OPEN**, sin asignar. Ningún PR abierto todavía. 21 PRs propios abiertos en REA (0 mergeados); 24 cerrados por mantenedores sin merge — viabilidad upstream incierta; decisión del propietario.
