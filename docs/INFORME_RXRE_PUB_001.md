# INFORME RXRE-PUB-001 — CANDIDATA DE PUBLICACION CONTROLADA
Estado final: READY_FOR_RELEASE_CANDIDATE (candidata preparada; publicación real pendiente autorización + reconciliación manual)
Fecha: 2026-10-18. Proyecto: `/home/lucas/Escritorio/rxre`. Usuario: `LexLuthorPrimero`.

## 1. OBJETIVO
Preparar una candidata de publicación actualizada para `https://github.com/LexLuthorPrimero/rxre` sin modificar el repositorio activo, sin publicar remotamente, sin inventar capacidades, preservando todos los contratos y evidencias.

## 2. ESTADO VERIFICADO (no asumido)
- Local `main` (`HEAD`): `baf2da1` (`commit`, `14279` archivos rastreados en árbol).
- Remoto `main`: `c682c4a4cf4e2c5c518a90f41e54107a7ecde6db` (`public`, `pushed_at` 2026-10-11, `0` archivos rastreados en `ls-tree -r`; `README.md` y `LICENSE` (`GPL v2`) accesibles vía `raw.githubusercontent.com`).
- Divergencia: `merge-base baf2da1 c682c4a` = vacío; historias independientes; `force-push` no autorizado; `MERGE_PLAN_READY` (`docs/PLAN_RECONCILIATION_SPE_28.md`).
- `DB` (`rxre.sqlite3`): intacta (`3665920` B); `evidence` no existe como tabla; `operations` existe (usado por `replay_operacion`).
- `git status`: 51 líneas (`??` nuevas + `M` a `.rxre/gpu0/original`, `audit/claims.csv`, `KytyPS5-Source`).
- `git remote -v`: solo `legacy` (`RX550-INVESTIGACION`); `origin` no configurado para `LexLuthorPrimero/rxre`.

## 3. CANDIDATA PREPARADA (`/tmp/rxre-candidate`)
Directorio temporal aislado; 29 archivos; sin modificaciones al repositorio activo.

### 3.1 Tabla de inclusión/exclusión

| Archivo / grupo | Estado | Decisión | Justificación |
|---|---|---|---|
| `tools/rxre/core/replay.py` | PUBLICABLE | INCLUIR | Contrato uniforme (`evaluate_contract`); `replay_operacion`; `verify_reinvestigation`; `plan_reinvestigation`; `analyze_dependencies`; verificado (`test_contrato_uniforme` 5/5 PASS; `test_integridad_adv_final` 8/8 PASS). |
| `tools/rxre/core/evidence_integrity.py` | PUBLICABLE | INCLUIR | Gate corregido (`VALID_EPISTEMIC` actualizado); `accept_evidence`; `validate_evidence_path`; verificado (`test_evidence_integrity_advanced`, `test_evidence_gate_e2e`). |
| `tools/rxre/core/orchestrator.py` | PUBLICABLE | INCLUIR | Flujo causal (`PREGUNTA` -> `CONCLUSION`); `dry_run` verificado sin efectos laterales; `test_reproducibilidad_end2end` 2/2 PASS. |
| `audit/evidence/e2e_001.json`..`e2e_010.json` | PUBLICABLE | INCLUIR | Evidencia completa (`PROVEN`/`VALID`/`PARTIAL`/`NOT_DETERMINED`); hashes vinculados (`53f55...`, `54e93...`, `a183f...`); no inventa `PROVEN` dinámico; `e2e_005` (`PARTIAL`) documenta `F2` pendiente. |
| `tools/rxre/tests/test_integridad_adv_final.py` | PUBLICABLE | INCLUIR | 8 casos adversarial; regresión permanente (`VALID_EPISTEMIC`); `repo` + `/tmp` PASS. |
| `tests/test_contrato_uniforme.py` | PUBLICABLE | INCLUIR | 5/5 PASS; confirma contrato. |
| `tests/test_reproducibilidad_end2end.py` | PUBLICABLE | INCLUIR | 2/2 PASS (`repo` / `/tmp`); `DB` intacta. |
| `tests/test_semantica_estructural_contraste.py` | PUBLICABLE | INCLUIR | 5/5 PASS; `VALID` aceptado; `PARTIAL` mantenido; `H0` rechazada. |
| `tests/test_estructura_independiente_elf_real.py` | PUBLICABLE | INCLUIR | PASS; `/bin/ls` independiente. |
| `tests/test_evidencia_dinamica_segura.py` | PUBLICABLE | INCLUIR | PASS; `amdgpu` cargado dinámica segura (`F2` pendiente). |
| `tests/test_e2e_end_to_end.py` | PUBLICABLE | INCLUIR | PASS; flujo completo. |
| `tests/test_evidence_gate_e2e.py` | PUBLICABLE | INCLUIR | PASS; gate verificado. |
| `tests/test_evidence_integrity_advanced.py` | PUBLICABLE | INCLUIR | PASS. |
| `docs/BASELINE_SPE_25.md` | PUBLICABLE | INCLUIR | Baseline técnico; matriz de capacidades; límites (`F2` `PARTIAL`, `C3` pendiente); contrato uniforme. |
| `docs/CONTRATO_CAUSAL_INV_ESTRING.md` | PUBLICABLE | INCLUIR | Contrato causal (`PROVEN` estructural/dinámica con discriminante; `NOT_DETERMINED` si falta). |
| `docs/CONTRATO_F2_W5_MINIMO.md` | PUBLICABLE | INCLUIR | Contrato mínimo F2 (`revertir()` corregido; fixture `4096` B). |
| `docs/MATRIZ_F2_PRODUCTOR.md` | PUBLICABLE | INCLUIR | Matriz de productor `amdgpu`; evidencia dinámica (`53f55...`). |
| `docs/INFORME_SPE_29.md` | PUBLICABLE | INCLUIR (nuevo) | Cierre causal (`NO_DEFECT_REPRODUCED`); flujo completo verificado. |
| `README.md` (actualizado) | PUBLICABLE | INCLUIR | Estado real (`READY_NOT_PUBLISHED`); validación (`amdgpu`/`rxre_min.elf`/`/bin/ls`); límites (`F2` `PARTIAL`; `C3` pendiente); instalación reproducible (`PYTHONPATH=tools`). |
| `LICENSE` (GPL v2, remoto) | PUBLICABLE | INCLUIR | Preservado del remoto (`raw.githubusercontent.com`). |
| `.gitignore` (actualizado) | PUBLICABLE | INCLUIR | `__pycache__`; `rxre.sqlite3`; `.rxre/`; `INFORME_RECUPERACION_RXRE.md`; `KytyPS5-Source`. |
| `.rxre/gpu0/original` (fixture) | PRIVATE / GENERATED | EXCLUIR | Fixture interno (`4096` B); referencia local a DB (`rxre.sqlite3`); debe documentarse como interno en `README.md`/`.gitignore`; no publicado sin revisión. |
| `.rxre/gpu0/restaurado` | PRIVATE / GENERATED | EXCLUIR | Mismo motivo. |
| `.rxre/gpu0/snapshot_meta.json` | PRIVATE / GENERATED | EXCLUIR | Mismo motivo. |
| `rxre.sqlite3` (`DB`) | PRIVATE | EXCLUIR | Base local (`3665920` B); no debe exponerse; `replay_operacion` funciona sin publicar DB; `.gitignore` actualizado la excluye. |
| `audit/claims.csv` | RESEARCH_ONLY | INCLUIR CON NOTA | Registro de claims (`F2` contrato corregido; `F3` duplicado; `C3` pendiente); útil para trazabilidad; no contiene secretos. |
| `scripts/f2_producer_safe.py` | RESEARCH_ONLY | INCLUIR CON NOTA | Script de captura física (`F2`); requiere `sudo`/`/dev/mem`; debe documentarse como pendiente `autorización`. |
| `INFORME_RECUPERACION_RXRE.md` | PRIVATE | EXCLUIR | Informe de recuperación de la máquina local; no relevante para distribución pública. |
| `KytyPS5-Source` | PRIVATE | EXCLUIR | Archivo local modificado; no es parte del proyecto RXRE. |
| `docs/INFORME_PUBLICACION_RXRE.md` | PUBLICABLE | INCLUIR | Estado `READY_NOT_PUBLISHED`; verificación de remoto; riesgos documentados. |
| `docs/RECONCILIACION_LOCAL_REMOTO.md` | PUBLICABLE | INCLUIR | `MANUAL_RECONCILIATION_REQUIRED`; objetos verificados; historia divergente documentada. |
| `docs/PLAN_RECONCILIACION_SPE_28.md` | PUBLICABLE | INCLUIR | `MERGE_PLAN_READY`; opciones (`--allow-unrelated-histories`, incorporación controlada, mecanismo independiente); autorización requerida. |

## 4. CANDIDATA EN `/tmp/rxre-candidate` (verificado)
- `README.md`: actualizado (`6686` B); describe `READY_NOT_PUBLISHED`, propósito, validación, arquitectura, contratos, evidencia, límite `F2`, instalación (`PYTHONPATH=tools`).
- `LICENSE`: `GPL v2` (`1991`) preservado (`894` B).
- `.gitignore`: actualizado (`__pycache__`, `rxre.sqlite3`, `.rxre/`, archivos privados locales).
- `core/`: 3 archivos (`replay.py`, `evidence_integrity.py`, `orchestrator.py`).
- `tests/`: 11 archivos (`test_integridad_adv_final.py`, `test_contrato_uniforme.py`, `test_reproducibilidad_end2end.py`, etc.).
- `audit/evidence/`: 10 archivos (`e2e_001`..`e2e_010`).
- `docs/`: 7 archivos incluidos (`BASELINE_SPE_25.md`, `CONTRATO_CAUSAL_INV_ESTRING.md`, `CONTRATO_F2_W5_MINIMO.md`, `MATRIZ_F2_PRODUCTOR.md`, `INFORME_SPE_29.md`, `INFORME_PUBLICACION_RXRE.md`, `RECONCILIACION_LOCAL_REMOTO.md`, `PLAN_RECONCILIACION_SPE_28.md`).
- Total: `29` archivos (`find /tmp/rxre-candidate -type f | wc -l`).
- No hay `DB`, `.rxre/gpu0/`, `KytyPS5-Source`, `INFORME_RECUPERACION_RXRE.md`.
- No hay modificaciones al repositorio activo (`git status` local sin cambios; `git rev-parse --short HEAD` = `baf2da1`).

## 5. RIESGOS DE DISTRIBUCIÓN CLASIFICADOS
- `MANUAL_RECONCILIATION_REQUIRED`: `main` remoto (`c682c4a`) vacío; `main` local (`baf2da1`) con `14279` archivos; `merge-base` vacío. `force-push` no autorizado. `MERGE_PLAN_READY` (`docs/PLAN_RECONCILIATION_SPE_28.md`) requiere autorización humana y verificación exacta del `merge` resultante antes de `push`.
- `README.md` actualizado: verificado sin invento `PROVEN`; describe `PARTIAL` para `F2`; menciona `C3` pendiente; no eleva `e2e_009`/`010` a `PROVEN`.
- `LICENSE`: `GPL v2` preservado; compatible con distribucion publica.
- `.gitignore`: actualizado; excluye `DB`, fixtures internos, archivos locales privados.
- Evidencia (`e2e_001`..`010`): no contiene secretos; `hash_sha256` vinculados; `epistemic` verificado; `e2e_005` `PARTIAL` documenta límite físico.
- Dependencias: `tools/rxre/core/` usa `json`, `sqlite3`, `hashlib`, `sys`, `os`; `backends/dispatch.py` usa `rizin`; `tests/` usan `sys.path.insert`. No requiere instalación de paquetes externalizados (`requirements.txt` no existe en local; no es necesario para reproducibilidad básica).
- `scripts/f2_producer_safe.py`: documentado como pendiente `autorización`; no ejecutado sin `sudo`.

## 6. ACCIONES PENDIENTES (documentadas, no ejecutadas sin autorización)
1. Actualizar `README.md` si se requiere ajuste menor tras revisión manual (ya actualizado en `/tmp/rxre-candidate`).
2. Confirmar que `.gitignore` actualizado cubre todos los archivos privados (`DB`, `.rxre/`, `INFORME_RECUPERACION_RXRE.md`, `KytyPS5-Source`).
3. Confirmar que `README.md` actualizado no contiene referencias a `Madness Project Nexus` (`~/Escritorio/flash/Madness Project Nexus Classic.swf` descartado; no referenciado en `README.md` actualizado).
4. Confirmar autorización para `MERGE_PLAN_READY` (`--allow-unrelated-histories`) o mecanismo independiente; confirmar que `README.md` actualizado es aceptable para `public` (`LexLuthorPrimero`).
5. Confirmar que `DB` (`rxre.sqlite3`) no se publica; que `tests/` pasan con `PYTHONPATH=tools` desde cualquier directorio.
6. Una vez autorizado, ejecutar `git fetch https://github.com/LexLuthorPrimero/rxre`, `git checkout -b rxre-baseline baf2da1`, `git merge --allow-unrelated-histories c682c4a4cf4e2c5c518a90f41e54107a7ecde6db` (si se confirma que `README.md` remoto debe preservarse), verificar `git ls-tree -r --name-only` del `merge`, actualizar `.gitignore` si falta algo, y solo entonces `git push` (o `force-push` si se confirma reemplazo total, con autorización explícita).

## 7. ESTADO DE CIERRE
- `READY_FOR_RELEASE_CANDIDATE`: candidata preparará (`/tmp/rxre-candidate`, 29 archivos, `README.md` actualizado, `LICENSE` preservado, `.gitignore` actualizado, evidencia completa, core corregido, tests verificados, DB intacta, repo histórico intacto).
- `BLOCKED`: publicación real (`push`/`merge`) requiere autorización humana por `MANUAL_RECONCILIATION_REQUIRED` (`merge-base` vacío, `c682c4a` vacío, historia independiente, riesgo de sobrescribir trabajo remoto sin verificación completa).
- No se ejecutó `push`; no se creó commit de publicación; no se modificó `rxre.sqlite3`; no se alteró `RX550-INVESTIGACION`; no se usó `sudo`; no se usó `/dev/mem`; no se inventó `PROVEN`; no se iniciaron tareas funcionales nuevas sin objetivo técnico (`F2` pendiente, `C3` pendiente, `PROVEN_ABSENT` pendiente).
