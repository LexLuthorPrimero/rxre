# RXRE — Reverse Engineering Engine

Estado: `READY_NOT_PUBLISHED` (candidata preparada para actualización controlada de `https://github.com/LexLuthorPrimero/rxre`).

## Propósito
RXRE es una plataforma de ingeniería inversa quirúrgica para IA basada en observación real, procedencia, razonamiento causal, pruebas discriminantes y validación epistemológica (`PROVEN`/`VALID`/`PARTIAL`/`NOT_DETERMINED`). No eleva afirmaciones a `PROVEN` automáticamente.

## Validación
- `amdgpu.ko` (`53f55...`) — módulo cargado (`e2e_001` a `e2e_005`); dinámica segura (`2735` `gfx` refs en `kallsyms`, `72` `polaris`); física (`F2`) pendiente autorización (`sudo`/`/dev/mem`).
- `/bin/ls` (`54e93...`) — evidencia independiente (`e2e_007` `VALID`, `e2e_008` `PARTIAL` `DATA` `main` `.rodata`, `e2e_009` `PARTIAL` semántica, `e2e_010` `PARTIAL` contraste). `CALL` no confirmada; dinámica pendiente.
- `rxre_min.elf` (`a183f...`) — evidencia cruzada (`e2e_006` `VALID`).

## Arquitectura real
- `core/replay.py`: `replay_operacion`, `plan_reinvestigation`, `verify_reinvestigation`, `evaluate_contract`, `analyze_dependencies`.
- `core/evidence_integrity.py`: `accept_evidence`, `validate_evidence_path`; `VALID_EPISTEMIC` actualizado (`VALID` incluido) — defecto corregido (`SPE 25`).
- `core/orchestrator.py`: `Orchestrator.run()` (`dry_run` verificado, sin efectos laterales).

## Contratos
- `evaluate_contract`: `COMPLETE` (precheck + ejecución `ok` + `BK_OK` sin `BK_EMPTY`); `PARTIAL` (limitaciones documentadas); `NOT_DETERMINED` (desconocido); `BLOCKED` (bloqueado); `INVALID_INPUT` (entrada inválida). Nunca `PROVEN` automático.
- `docs/CONTRATO_CAUSAL_INV_ESTRING.md`: `PROVEN` solo con evidencia estructural + dinámica confirmada + discriminante validado; `NOT_DETERMINED` cuando falta universo de búsqueda (`C3`).

## Evidencia (`audit/evidence/e2e_001`..`e2e_010`)
- `e2e_001`: `amdgpu.ko` (`PROVEN` estructural).
- `e2e_002`: relación estructural (`PROVEN`).
- `e2e_003`: inversa causal (`NOT_DETERMINED`).
- `e2e_004`: frontera `amdgpu` (`PARTIAL`).
- `e2e_005`: dinámica segura (`PARTIAL` — `F2` pendiente).
- `e2e_006`: cruzada (`rxre_min.elf`, `VALID`).
- `e2e_007`: independiente (`/bin/ls`, `VALID`).
- `e2e_008`: estructural (`/bin/ls` `main` `DATA`, `PARTIAL`).
- `e2e_009`: semántica (`main` `.rodata`, `PARTIAL`).
- `e2e_010`: contraste (`DATA` confirmada; `CALL` no confirmada; `PARTIAL`).

## Pruebas (`tests/`)
- Adversarial (`test_integridad_adv_final.py`): 8/8 PASS (`hash` alterado, esquema inválido, procedencia inconsistente, archivo vacío, otro artefacto, evidencia correcta, `dry_run`, dict inválido).
- Contrato (`test_contrato_uniforme.py`): 5/5 PASS.
- Reproducibilidad (`test_reproducibilidad_end2end.py`): 2/2 PASS (repo + `/tmp`).
- Semántica (`test_semantica_estructural_contraste.py`): 5/5 PASS (`VALID` aceptado tras corrección; `PARTIAL` mantenido; `H0` rechazada para estructura).

## Estado de publicación
- Remoto: `https://github.com/LexLuthorPrimero/rxre` (`public`, `main`: `c682c4a4cf4e2c5c518a90f41e54107a7ecde6db`, `0` archivos rastreados, `README.md`/`LICENSE` (`GPL v2`) accesibles).
- Local (`main`: `baf2da1`): `14279` archivos rastreados (core, tests, fixtures internos, evidencia, docs, scripts).
- Divergencia: `merge-base` vacío (`histories` independientes); `c682c4a` vacío (`ls-tree` `0` archivos); `README.md`/`LICENSE` remotos accesibles pero no rastreados en `c682c4a`.
- Reconciliación (`docs/RECONCILIACION_LOCAL_REMOTO.md`): `MANUAL_RECONCILIATION_REQUIRED`; `docs/PLAN_RECONCILIACION_SPE_28.md`: `MERGE_PLAN_READY` (plan no destructivo respaldado por evidencia).
- Publicación: `READY_NOT_PUBLISHED`; no se realiza `push` ni `force-push` sin autorización; `SPE 29` confirma `NO_DEFECT_REPRODUCED`.

## Limitaciones (`F2` pendiente; `C3` pendiente; `MANUAL_RECONCILIATION_REQUIRED` pendiente)
- `F2` (`/dev/mem` / captura física `RX 550` / dinámico `amdgpu`): pendiente `sudo`/`autorización`. `e2e_005` (`PARTIAL`) documenta límite exacto (`2735` `gfx` refs, `72` `polaris` refs en `kallsyms`; dinámica sin captura física).
- `C3` (`PROVEN_ABSENT`): pendiente definición de universo de búsqueda (`amdgpu` cargado; `rxre_min.elf`; `/bin/ls`). No se asigna sin criterio de cobertura (`docs/CONTRATO_CAUSAL_INV_ESTRING.md`).
- `MANUAL_RECONCILIATION_REQUIRED`: publicación remota requiere revisión manual (`README.md` actualizado sin inventos `PROVEN`; `.gitignore` actualizado para `.rxre/gpu0/`; `DB` `rxre.sqlite3` mantenida privada).

## Instalación y uso (reproducible desde cualquier directorio)
```bash
PYTHONPATH=tools python3 -m pytest tools/rxre/tests/test_integridad_adv_final.py -q
PYTHONPATH=tools python3 -c "
import sys; sys.path.insert(0,'tools/rxre')
from rxre.core.evidence_integrity import accept_evidence
print('Gate:', accept_evidence('audit/evidence/e2e_007.json', '/bin/ls')['status'])
"
```

## Notas de versión (`SPE 25` a `SPE 29`)
- `SPE 25`: baseline técnico (`BASELINE_SPE_25.md`); contrato uniforme (`COMPLETE`/`PARTIAL`/`NOT_DETERMINED`); adversarial 8/8 PASS; reproducibilidad 2/2 PASS; `DB` intacta.
- `SPE 26`: publicación controlada (`READY_NOT_PUBLISHED`); `docs/INFORME_PUBLICACION_RXRE.md`; remoto verificado (`c682c4a` vacío, `README.md`/`GPL v2` accesibles); `DB` sin inventos; `e2e_001`..`010` preservados.
- `SPE 27`: reconciliación (`MANUAL_RECONCILIATION_REQUIRED`); `docs/RECONCILIACION_LOCAL_REMOTO.md`; historia divergente confirmada (`merge-base` vacío); `baf2da1` (`14279` archivos) vs `c682c4a` (`0` rastreados).
- `SPE 28`: plan de reconciliación (`MERGE_PLAN_READY`); `docs/PLAN_RECONCILIACION_SPE_28.md`; opciones (`--allow-unrelated-histories`, incorporación controlada, mecanismo independiente); autorización humana requerida antes de `push`/`merge`.
- `SPE 29`: cierre causal (`NO_DEFECT_REPRODUCED`); `docs/INFORME_SPE_29.md`; flujo causal completo (`PREGUNTA` -> `SIGUIENTE ACCION`) verificado; `F2` pendiente; `C3` pendiente; `PROVEN` nunca automático.

## Referencias y archivos descartados
- `~/Escritorio/flash/Madness Project Nexus Classic.swf`: archivo descartado (`Madness Project Nexus`); no usado como requisito ni bloqueo; no analizado; no ejecutado; no referenciado en `README` ni contrato.
- `.rxre/gpu0/` (`original`, `restaurado`, `snapshot_meta.json`): fixtures internos (`4096B`); documentados en contrato `F2`; no publicados sin revisión explícita (`.gitignore` actualizado debe excluirlos o `README.md` debe documentarlos como internos).
- `audit/claims.csv`: registro de claims (`F2` contrato corregido; `F3` duplicado documentado; `C3` pendiente); incluido en candidato con nota interna.
