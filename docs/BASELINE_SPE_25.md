# BASELINE SPE 25 — CIERRE TECNICO RXRE

Fecha: 2026-10-18. Fase: cierre de desarrollo (SPE 25). No inicia SPE 27 sin objetivo técnico nuevo.

## 1. ALCANCE DE ESTA FASE
- Verificar integridad adversarial end-to-end (8 casos sistemáticos).
- Corregir defecto real encontrado (`VALID_EPISTEMIC` rechazaba `VALID`; corregido en `core/evidence_integrity.py`).
- Confirmar reproducibilidad (`repo` y `/tmp`).
- Documentar matriz capacidad -> implementación -> evidencia -> prueba.
- No modificar DB (`rxre.sqlite3` intacta, sin tabla `evidence`, sin registros inventados).
- No modificar `/home/lucas/Escritorio/RX550-INVESTIGACION`.
- No crear ramas / worktrees / commits; no usar `git reset/restore/checkout/clean/stash`.

## 2. ARQUITECTURA FUNCIONAL REAL (rutas exactas)
- `core/replay.py`: `replay_operacion`, `plan_reinvestigation`, `verify_reinvestigation`, `evaluate_contract`
- `core/evidence_integrity.py`: `accept_evidence`, `validate_evidence_path`; `VALID_EPISTEMIC` actualizado (`VALID` incluido)
- `core/orchestrator.py`: `Orchestrator.run()` con `dry_run`; flujo `ENTRADA -> IDENTIDAD -> INTEGRIDAD -> PROCEDENCIA -> CONTRATO -> CLAIM`
- `backends/dispatch.py`: ejecución de `binary.xrefs`, `binary.inspect`
- `tests/`: `test_integridad_adv_final.py` (8 casos adversarial), `test_contrato_uniforme.py`, `test_reproducibilidad_end2end.py`, `test_evidencia_gate_e2e.py`, `test_estructura_independiente_elf_real.py`, `test_evidencia_dinamica_segura.py`, `test_semantica_estructural_contraste.py`
- `audit/evidence/e2e_001.json` a `e2e_010.json`: preservadas; nuevas `e2e_009` y `e2e_010`; `e2e_007` verificada con `VALID`
- `docs/CONTRATO_CAUSAL_INV_ESTRING.md`: contrato causal (`PROVEN` estructural; `NOT_DETERMINED` dinámica)

## 3. MATRIZ DE CAPACIDADES (implementación / evidencia / test / alcance)

| Capacidad | Implementación | Evidencia | Test / Verificación | Estado |
|---|---|---|---|---|
| Inspección estructural ELF | `binary.inspect` (dispatch) | `e2e_006` (rxre_min.elf), `e2e_007` (/bin/ls) | `test_estructura_independiente_elf_real.py` | IMPLEMENTADA / VALIDADA EN ALCANCE LIMITADO |
| Adquisición y procedencia de evidencia | `accept_evidence`, `validate_evidence_path`, `core/replay.py` | `e2e_001` a `e2e_010`; hashes `sha256` vinculados a artefactos reales | `test_evidencia_gate_e2e.py`; `test_integridad_adv_final.py` (casos 1-4,6) | IMPLEMENTADA / VALIDADA EN ALCANCE LIMITADO |
| Integridad y gate | `core/evidence_integrity.py` (corregido); `VALID_EPISTEMIC` actualizado | `e2e_007` aceptada tras corrección; `e2e_010` aceptada; evidencia alterada rechazada (caso 1) | `test_integridad_adv_final.py` 8/8 PASS; `test_evidence_integrity_advanced.py` | IMPLEMENTADA / VALIDADA EN ALCANCE LIMITADO |
| Evaluación contractual (`evaluate_contract`) | `core/replay.py`; distingue `BK_OK`/`BK_INVALID`/`BK_ERROR`/`BK_EMPTY`; `COMPLETE`/`PARTIAL`/`NOT_DETERMINED`/`BLOCKED` | `e2e_005` (`PARTIAL`), `e2e_009` (`PARTIAL`), `e2e_010` (`PARTIAL`), `e2e_006` (`VALID`) | `test_contrato_uniforme.py` 5/5 PASS; `test_integridad_adv_final.py` (casos 5,8) | IMPLEMENTADA / VALIDADA EN ALCANCE LIMITADO |
| Hipótesis / plan / conclusión (`Orchestrator`) | `core/orchestrator.py`; `plan_reinvestigation`; `dry_run` sin efectos laterales | `e2e_003`, `e2e_004` (frontera); `Orchestrator.run()` integrado con replay | `test_reproducibilidad_end2end.py`; `test_integridad_adv_final.py` caso 7 | IMPLEMENTADA / VALIDADA EN ALCANCE LIMITADO |
| Replay / reinvestigación | `replay_operacion`; `verify_reinvestigation`; `analyze_dependencies` | `e2e_005` (`amdgpu` cargado), `e2e_006` (cruzada) | `test_e2e_end_to_end.py`; `test_reproducibilidad_end2end.py` 2/2 PASS | IMPLEMENTADA / VALIDADA EN ALCANCE LIMITADO |
| Relaciones estructurales / xrefs | `binary.xrefs` (rizin backend); `iS`; `python3` bytes | `e2e_008` (74 nodos DATA), `e2e_009`, `e2e_010` (`main` DATA 15940-16384) | `test_semantica_estructural_contraste.py`; `test_semantica_xrefs_elf_real.py`; 5/5 PASS | IMPLEMENTADA / VALIDADA EN ALCANCE LIMITADO |
| Reproducción (`repo` y `/tmp`) | `PYTHONPATH=tools`; `run` desde CWD arbitrario | Todas las evidencias; fixtures `.rxre/gpu0/original` (4096b, contrato F2 corregido) | `test_integridad_adv_final.py` en `/tmp`; `test_reproducibilidad_end2end.py` | IMPLEMENTADA / VALIDADA EN ALCANCE LIMITADO |
| Pruebas adversariales / regresiones | `test_integridad_adv_final.py`; `test_evidence_integrity_advanced.py`; `test_evidence_gate_e2e.py` | 8 casos cubiertos (hash alterado, esquema inválido, procedencia inconsistente, archivo vacío, otro artefacto, evidencia correcta, dry_run, dict inválido) | 8/8 PASS repo; 8/8 PASS /tmp tras corrección `VALID` | IMPLEMENTADA / VALIDADA EN ALCANCE LIMITADO |

Nota de alcance: ninguna capacidad está declarada como universalmente verificada para todos los artefactos posibles. Cada verificación se vincula a los casos concretos documentados (`e2e_001`–`e2e_010`) y a los tests que los ejercitan.

## 4. DEFECTOS CORREGIDOS Y REGRESIONES
- **Defecto real 25**: `VALID_EPISTEMIC` no incluía `VALID`. Consecuencia: `accept_evidence` rechazaba `e2e_007.json` (y cualquier evidencia con `epistemic="VALID"`).
- **Corrección mínima**: editar `tools/rxre/core/evidence_integrity.py` (agregar `"VALID"` al set); no se alteró el resto del contrato.
- **Regresión confirmada**: `test_integridad_adv_final.py` caso 6 (`evidencia_correcta_aceptada`) pasa tras corrección; caso 1 (`hash_alterado`) rechaza correctamente; casos 2-4 rechazan; caso 7 (`dry_run`) no alteró archivos.
- **Defecto F2 (preexistente, corregido previamente en SPE)**: contrato `revertir()` usaba directorio en lugar de archivo; corregido con fixture `.rxre/gpu0/original` (4096 bytes) y meta asociada.
- **Defectos documentados (no corregidos, fuera de alcance)**: `F3`/`F4` duplicados por diseño (`COLISION` determinista); `C3` (`PROVEN_ABSENT`) requiere universo de búsqueda definido antes de asignar; `W5` (`PARTIAL`) documentado por límite físico (`/dev/mem`).

## 5. LIMITES EXPLICITOS (no ocultos)
- **F2 físico (`/dev/mem`)**: evidencia dinámica segura (`e2e_005`, `amdgpu` cargado + `kallsyms`) existe; captura física requiere `sudo` + acceso a memoria del kernel RX 550; no autorizado en esta fase. Estado: `PARTIAL`; límite exacto documentado en `e2e_005.json` y contrato F2.
- **C3 (`PROVEN_ABSENT`)**: no asignado sin un universo de búsqueda definido y un criterio de cobertura suficiente. No se afirma que `amdgpu.ko` esté completamente ausente de la dinámica; se afirma que la evidencia dinámica no confirma `PROVEN` de ausencia.
- **Relaciones semánticas `/bin/ls` (`e2e_009`, `e2e_010`)**: `DATA` verificada estructuralmente (74 nodos, `main` `.rodata` 15940-16384); `CALL` no confirmada; dinámica no confirmada (`PARTIAL`). No se eleva automáticamente a `PROVEN`.
- **Generalización**: verificado en `/bin/ls` (ELF64 real, 153400B, `54e93...`), `rxre_min.elf` (fixture 4728B), `amdgpu.ko` (módulo cargado, `53f55...`). No se asume que los resultados se generalizan a otros artifacts sin evidencia adicional.
- **DB / repositorio histórico (`RX550-INVESTIGACION`)**: no tocado; no se crean nuevos registros de evidencia en DB; `e2e_001`–`e2e_010` son archivos independientes, no entradas DB.

## 6. COMANDOS DE REPRODUCCION (verificables)
```bash
# Desde /home/lucas/Escritorio/rxre (repo o /tmp)
PYTHONPATH=tools python3 tools/rxre/tests/test_integridad_adv_final.py
PYTHONPATH=tools python3 tools/rxre/tests/test_contrato_uniforme.py
PYTHONPATH=tools python3 tools/rxre/tests/test_reproducibilidad_end2end.py
PYTHONPATH=tools python3 -c "
import sys; sys.path.insert(0,'tools/rxre')
from rxre.core.evidence_integrity import accept_evidence
print(accept_evidence('audit/evidence/e2e_007.json','/bin/ls'))
"
# Verificación de gate corregido (VALID aceptado)
sha256sum /bin/ls  # 54e936d37decdad9ecaf189b1de347605a0a99037ec87bd17679b6cbde871a0c
```

## 7. ESTADO DE ARTIFACTOS Y EVIDENCIA
- `/bin/ls`: ELF64, 153400 bytes, hash `54e936...`; evidencia `e2e_007` (`VALID`), `e2e_008` (`PARTIAL`), `e2e_009` (`PARTIAL`), `e2e_010` (`PARTIAL`); no modificado; no sobrescrito
- `rxre_min.elf`: fixture 4728B; hash `a183f...`; evidencia `e2e_006` (`VALID`)
- `amdgpu.ko`: hash `53f55...`; evidencia `e2e_001`, `e2e_002`, `e2e_003`, `e2e_004` (`PARTIAL`/`NOT_DETERMINED`), `e2e_005` (`PARTIAL`)
- `e2e_001` a `e2e_010`: todos presentes; ninguno sobrescrito; `e2e_009` y `e2e_010` son nuevos; `e2e_007` verificado tras corrección

## 8. RIESGOS Y CUESTIONES ABIERTAS (documentados, no ocultos)
- F2 requiere autorización; sin ella, ninguna dinámica de hardware de RX 550 puede ser declarada `PROVEN`.
- `C3` requiere definición de universo; sin ello, no debe asignarse `PROVEN_ABSENT`.
- Relaciones semánticas de `/bin/ls` permanecen `PARTIAL`; cualquier elevación a `PROVEN` requiere confirmación dinámica o hardware, no solo `DATA`.

## 9. CRITERIOS OBJETIVOS PARA REABRIR DESARROLLO
- Si se autoriza `sudo` / `/dev/mem`: ejecutar `f2_producer_safe.py` con contrato F2 corregido; objetivo: completar `PARTIAL` -> `VALID` dinámico para `amdgpu` / RX 550.
- Si aparece nuevo artefacto independiente (ELF, módulo, fixture): crear `e2e_011` siguiendo el flujo `ENTRADA -> IDENTIDAD -> INTEGRIDAD -> PROCEDENCIA -> CONTRATO`; no reutilizar hashes ni resultados previos sin verificación.
- Si se detecta nuevo defecto en `accept_evidence`, `evaluate_contract` u `Orchestrator`: documentar, reproducir, corregir con cambio mínimo, agregar regresión en `test_integridad_adv_final.py`.

## 10. CIERRE FORMAL
- Fase SPE 25 cerrada.
- Defecto real corregido y verificado (8/8 PASS).
- Base técnica reproducible desde `repo` y `/tmp`.
- No iniciado SPE 27.
- Estado: `COMPLETE` (implementación + evidencia + contrato + prueba) con límites explícitos (`F2 PARTIAL`, `C3 pendiente`, `DATA PARTIAL`).
