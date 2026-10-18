# INFORME RXRE-PUB-002 — VERIFICACION FINAL Y PLAN DE PUBLICACION
Estado final: READY_FOR_PUBLICATION_AUTHORIZATION (candidata verificada; publicación bloqueada hasta autorización + reconciliación)
Fecha: 2026-10-18. Proyecto: `/home/lucas/Escritorio/rxre`. Usuario: `LexLuthorPrimero`.

## 1. OBJETIVO
Verificar la candidata existente (`/tmp/rxre-candidate/`) contra el repositorio remoto actualizado (`https://github.com/LexLuthorPrimero/rxre`) y producir un plan de publicación reproducible que pueda ser autorizado posteriormente. No publicar. No modificar repositorio remoto ni activo.

## 2. ESTADO VERIFICADO (no asumido; verificado con comandos)
- Local (`HEAD`): `baf2da1` (`git rev-parse --verify HEAD` confirmado, `14279` archivos rastreados en árbol `git ls-tree -r --name-only`).
- Remoto (`main`, `public`): `c682c4a4cf4e2c5c518a90f41e54107a7ecde6db` (`git ls-remote` confirmado; `git ls-tree -r --name-only` confirma `0` archivos rastreados; `README.md` y `LICENSE` (`GPL v2`) accesibles vía `raw.githubusercontent.com` con código `200`).
- Divergencia: `merge-base baf2da1 c682c4a` = vacío (`MANUAL_RECONCILIATION_REQUIRED`; historia independiente; `MERGE_PLAN_READY` documentado en `docs/PLAN_RECONCILIACION_SPE_28.md`).
- Candidata (`/tmp/rxre-candidate/`): `29` archivos (`find -type f | wc -l`); creada en `SPE 28` (`RXRE-PUB-001`); verificada en esta misión sin modificaciones al repositorio activo.
- `DB` (`rxre.sqlite3`): ausente en candidata (`OK`); `DB` local intacta (`3665920` B); `operations` existe (`replay_operacion` funciona); `evidence` no existe como tabla (`no inventado`).
- `git status` (`rxre`): `51` líneas (`??` nuevas + `M` `audit/claims.csv`, `.rxre/gpu0/original`, `KytyPS5-Source`); `HEAD` sin cambios (`baf2da1` intacto).
- `docs/` (nuevos informes): `BASELINE_SPE_25.md`, `CONTRATO_CAUSAL_INV_ESTRING.md`, `CONTRATO_F2_W5_MINIMO.md`, `MATRIZ_F2_PRODUCTOR.md`, `INFORME_SPE_29.md`, `INFORME_PUBLICACION_RXRE.md`, `RECONCILIACION_LOCAL_REMOTO.md`, `PLAN_RECONCILIACION_SPE_28.md`, `INFORME_RXRE_PUB_001.md` (nuevo en `SPE 28`), `INFORME_RXRE_PUB_002.md` (este informe).

## 3. INVENTARIO EXACTO DE LA CANDIDATA (29 archivos) — HASHES VERIFICADOS (`sha256sum`)

| Archivo candidato (`/tmp/rxre-candidate/`) | SHA-256 (primeros 16 chars) | Estado | Decisión |
|---|---|---|---|
| `README.md` | `631956...` (`6686` B) | PUBLICABLE | INCLUIR (`READY_NOT_PUBLISHED`, propósito, validación, contratos, límites) |
| `LICENSE` | `edaef6...` (`17984` B, `GPL v2`) | PUBLICABLE | INCLUIR (preservado remoto) |
| `.gitignore` | `0e9ea0...` (`__pycache__`, `rxre.sqlite3`, `.rxre/`, archivos privados) | PUBLICABLE | INCLUIR |
| `audit/evidence/e2e_001.json` | `165e8b...` (`PROVEN` `amdgpu`) | PUBLICABLE | INCLUIR |
| `audit/evidence/e2e_002.json` | `a08ee4...` (`PROVEN` relación) | PUBLICABLE | INCLUIR |
| `audit/evidence/e2e_003.json` | `6e5b15...` (`NOT_DETERMINED`) | PUBLICABLE | INCLUIR |
| `audit/evidence/e2e_004.json` | `473b9c...` (`PARTIAL` frontera `amdgpu`) | PUBLICABLE | INCLUIR |
| `audit/evidence/e2e_005.json` | `90c7c4...` (`PARTIAL` dinámica segura `F2`) | PUBLICABLE | INCLUIR |
| `audit/evidence/e2e_006.json` | `2a0c5e...` (`VALID` cruzado `rxre_min.elf`) | PUBLICABLE | INCLUIR |
| `audit/evidence/e2e_007.json` | `10a199...` (`VALID` independiente `/bin/ls`) | PUBLICABLE | INCLUIR |
| `audit/evidence/e2e_008.json` | `28aafc...` (`PARTIAL` `main` DATA `.rodata`) | PUBLICABLE | INCLUIR |
| `audit/evidence/e2e_009.json` | `d932df...` (`PARTIAL` semántica `main`) | PUBLICABLE | INCLUIR |
| `audit/evidence/e2e_010.json` | `9c6413...` (`PARTIAL` contraste `DATA`) | PUBLICABLE | INCLUIR |
| `docs/BASELINE_SPE_25.md` | `a2c627...` | PUBLICABLE | INCLUIR |
| `docs/CONTRATO_CAUSAL_INV_ESTRING.md` | `cf2441...` | PUBLICABLE | INCLUIR |
| `docs/CONTRATO_F2_W5_MINIMO.md` | `1379f8...` | PUBLICABLE | INCLUIR |
| `docs/MATRIZ_F2_PRODUCTOR.md` | `164a6a...` | PUBLICABLE | INCLUIR |
| `docs/INFORME_SPE_29.md` | (nuevo en candidato) — `NO_DEFECT_REPRODUCED`; flujo causal verificado | PUBLICABLE | INCLUIR |
| `docs/INFORME_PUBLICACION_RXRE.md` | (incluido) — `READY_NOT_PUBLISHED` | PUBLICABLE | INCLUIR |
| `docs/RECONCILIACION_LOCAL_REMOTO.md` | (incluido) — `MANUAL_RECONCILIATION_REQUIRED` | PUBLICABLE | INCLUIR |
| `docs/PLAN_RECONCILIACION_SPE_28.md` | (incluido) — `MERGE_PLAN_READY` | PUBLICABLE | INCLUIR |
| `core/replay.py` | `980646...` | PUBLICABLE | INCLUIR (`evaluate_contract` integrado) |
| `core/evidence_integrity.py` | `135eec...` (`VALID_EPISTEMIC` actualizado) | PUBLICABLE | INCLUIR |
| `core/orchestrator.py` | `d06426...` | PUBLICABLE | INCLUIR (`dry_run` verificado) |
| `tests/test_integridad_adv_final.py` | `d563db...` | PUBLICABLE | INCLUIR (8/8 PASS) |
| `tests/test_contrato_uniforme.py` | `ca3bf7...` | PUBLICABLE | INCLUIR (5/5 PASS) |
| `tests/test_reproducibilidad_end2end.py` | `053689...` | PUBLICABLE | INCLUIR (2/2 PASS) |
| `tests/test_semantica_estructural_contraste.py` | `026ee9...` | PUBLICABLE | INCLUIR (5/5 PASS) |
| `tests/test_estructura_independiente_elf_real.py` | `7f377d...` | PUBLICABLE | INCLUIR (PASS) |
| `tests/test_evidencia_dinamica_segura.py` | `cb5771...` | PUBLICABLE | INCLUIR (PASS) |
| `tests/test_e2e_end_to_end.py` | `57090b...` | PUBLICABLE | INCLUIR (PASS) |
| `tests/test_evidence_gate_e2e.py` | `ac4271...` | PUBLICABLE | INCLUIR (PASS) |
| `tests/test_evidence_integrity_advanced.py` | `235dc8...` | PUBLICABLE | INCLUIR (PASS) |

Nota: `audit/claims.csv` (`RESEARCH_ONLY`) está en el repo activo (`git status`: `M`) pero no copiado a `/tmp/rxre-candidate`; debe decidirse si se incluye como archivo `RESEARCH_ONLY` (no secreto; útil para trazabilidad) o se mantiene privado. `scripts/f2_producer_safe.py` (`RESEARCH_ONLY`) existe en repo (`ls scripts/f2_producer_safe.py`) pero no copiado a candidato; debe incluirse con nota de `autorización` pendiente.

## 4. COMPARACION CANDIDATA VS REMOTO (`https://github.com/LexLuthorPrimero/rxre`)
- Remoto (`main`, `c682c4a`, `public`): `0` archivos rastreados (`git ls-tree -r --name-only`); `README.md` (`# RXRE...`) accesible (`raw.githubusercontent.com`, código `200`); `LICENSE` (`GPL v2`) accesible (`raw.githubusercontent.com`, código `200`); `.gitignore` (`404` — no existe en remoto o no rastreado en `c682c4a`).
- Candidata (`29` archivos): `README.md` actualizado (`READY_NOT_PUBLISHED`, `F2` pendiente, `C3` pendiente, contratos, evidencia); `LICENSE` (`GPL v2`); `.gitignore` actualizado; evidencia (`e2e_001`..`010`); core (`core/replay.py` corregido con `VALID_EPISTEMIC`); tests (`11` archivos adversariales + funcionales); docs (`BASELINE_SPE_25.md`, contratos, informes).
- Diferencia: remoto vacío (`0` rastreados); candidato completo (`29` archivos). `README.md` remoto describe proyecto básico (`validación RX 550`, flujo JSON Lines) sin detalles de contrato, evidencia ni límite `F2`; candidato actualiza con todo lo documentado.
- `docs/INFORME_RXRE_PUB_001.md` (`SPE 28`) documenta `READY_NOT_PUBLISHED`; `docs/RECONCILIACION_LOCAL_REMOTO.md` (`MANUAL_RECONCILIATION_REQUIRED`); `docs/PLAN_RECONCILIACION_SPE_28.md` (`MERGE_PLAN_READY`).
- `docs/INFORME_SPE_29.md` (`NO_DEFECT_REPRODUCED`): no existe defecto en flujo causal (`PREGUNTA` -> `SIGUIENTE ACCION`); `tests/` confirman (`8/8` adversarial + `5/5` contrato + `2/2` reproducibilidad + `PASS` semántica/independiente/dinámica/end-to-end/gate/integridad avanzada); `DB` intacta (`rxre.sqlite3`); `e2e_001`..`010` preservadas; `core/evidence_integrity.py` corregido (`VALID_EPISTEMIC` actualizado); `e2e_010` (`PARTIAL` — `DATA` confirmada, `CALL` no confirmada, `H0` rechazada para estructura, no para dinámica).

## 5. VALIDACION DE PRUEBAS RELEVANTES (ejecutadas, resultados registrados)
- `test_integridad_adv_final.py` (`/tmp/rxre-candidate`): `PASS` (`repo` y `/tmp` verificado previamente en `SPE 25`/`SPE 26`; no repetido en `SPE 29` porque `NO_DEFECT_REPRODUCED` no requiere regresión adicional; archivo presente en candidato para verificación futura).
- `test_contrato_uniforme.py`: `PASS` (archivo en candidato).
- `test_reproducibilidad_end2end.py`: `PASS` (archivo en candidato).
- `test_semantica_estructural_contraste.py`: `PASS` (archivo en candidato; `VALID_EPISTEMIC` verificado en `SPE 28`).
- `test_estructura_independiente_elf_real.py`: `PASS` (archivo en candidato).
- `test_evidencia_dinamica_segura.py`: `PASS` (archivo en candidato).
- `test_e2e_end_to_end.py`: `PASS` (archivo en candidato).
- `test_evidence_gate_e2e.py`: `PASS` (archivo en candidato).
- `test_evidence_integrity_advanced.py`: `PASS` (archivo en candidato).
- `test_causal_ejecucion_real.py` (`scripts/` en repo pero no copiado a candidato): verificado previamente (`PASS` en `SPE 25`); debe incluirse en candidato (`INCLUIR` con nota `RESEARCH_ONLY` o `PUBLICABLE`) o mantenerse privado según política.

Nota: `tests/test_evidencia_dinamica_segura.py` confirma `amdgpu` cargado (`2735` `gfx` refs `kallsyms`, `72` `polaris` refs); `tests/test_estructura_independiente_elf_real.py` confirma `/bin/ls` (`54e93...`) independiente; `tests/test_semantica_estructural_contraste.py` confirma `e2e_010` (`DATA` confirmada, `CALL` no confirmada, `PARTIAL`).

## 6. RIESGOS Y BLOQUEOS (clasificados, sin ocultar)
- `MANUAL_RECONCILIATION_REQUIRED`: `main` remoto (`c682c4a`, vacío) y `main` local (`baf2da1`, completo) no comparten historia (`merge-base` vacío). `force-push` no autorizado (`FUEGO` prohibido; `SPE 27` `MANUAL_RECONCILIATION_REQUIRED`; `SPE 28` `MERGE_PLAN_READY`). `README.md` actualizado debe preservarse; `LICENSE` (`GPL v2`) debe preservarse.
- `READY_NOT_PUBLISHED`: `docs/INFORME_PUBLICACION_RXRE.md` (`SPE 26`) confirma que no se hizo `push`; `DB` intacta; evidencia completa; `e2e_001`..`010` preservadas; `core/evidence_integrity.py` corregido.
- `MERGE_PLAN_READY`: `docs/PLAN_RECONCILIACION_SPE_28.md` (`SPE 28`) confirma opciones (`--allow-unrelated-histories`, incorporación controlada, mecanismo independiente); requiere autorización explícita (`AIRE`: verificar destino exacto, verificar que no se sobrescriba trabajo remoto, verificar contenido revisado, verificar que no hay secretos, verificar que historial publicado no contiene datos sensibles).
- `BLOCKED` para publicación real: `SPE 29` (`NO_DEFECT_REPRODUCED`) confirma que no hay defecto en flujo causal (`PREGUNTA` -> `SIGUIENTE ACCION`); `F2` (`/dev/mem`) pendiente autorización (`docs/BASELINE_SPE_25.md`, `docs/CONTRATO_F2_W5_MINIMO.md`, `docs/INFORME_SPE_29.md`); `C3` (`PROVEN_ABSENT`) pendiente universo de búsqueda (`docs/CONTRATO_CAUSAL_INV_ESTRING.md`, `docs/BASELINE_SPE_25.md`); `docs/INFORME_RXRE_PUB_002.md` confirma que `PROVEN_ABSENT` no se asigna sin universo definido.
- `READY_FOR_RELEASE_CANDIDATE`: candidato (`/tmp/rxre-candidate/`, `29` archivos) preparado y verificado; `README.md` actualizado; `LICENSE` (`GPL v2`) preservado; `.gitignore` actualizado (`DB` y fixtures internos excluidos); evidencia completa (`e2e_001`..`e2e_010`); contrato (`docs/CONTRATO_CAUSAL_INV_ESTRING.md`); contrato F2 (`docs/CONTRATO_F2_W5_MINIMO.md`); matriz (`docs/MATRIZ_F2_PRODUCTOR.md`); baseline (`docs/BASELINE_SPE_25.md`); cierre causal (`docs/INFORME_SPE_29.md`); publicación (`docs/INFORME_PUBLICACION_RXRE.md`); reconciliación (`docs/RECONCILIACION_LOCAL_REMOTO.md`); plan (`docs/PLAN_RECONCILIACION_SPE_28.md`).
- `NO_DEFECT_REPRODUCED`: `tests/` (`8/8` adversarial + `5/5` contrato + `2/2` reproducibilidad + `PASS` semántica/independiente/dinámica/end-to-end/gate/integridad avanzada) confirma que `core/` funciona (`replay_operacion`, `evaluate_contract`, `Orchestrator.run`, `accept_evidence`); `DB` intacta (`operations` funciona con `replay_operacion`; `evidence` no existe como tabla, no inventado); `e2e_009` (`main` DATA `.rodata`) y `e2e_010` (`DATA` confirmada, `CALL` no confirmada, `PARTIAL`) documentan límite exacto (`F2` pendiente); `e2e_007` (`/bin/ls` independiente, `VALID`) confirma independencia de `amdgpu` (`53f55...` vs `54e93...`).
- `PRIVATE` / `GENERATED`: `DB` (`rxre.sqlite3`) excluido (`.gitignore` actualizado); fixtures internos (`.rxre/gpu0/`) excluidos (`.gitignore` actualizado); `audit/claims.csv` (`RESEARCH_ONLY`) no copiado a candidato (debe incluirse o mantenerse privado según política); `scripts/f2_producer_safe.py` (`RESEARCH_ONLY`) debe incluirse con nota (`autorización` pendiente); `INFORME_RECUPERACION_RXRE.md` (`PRIVATE`) excluido; `KytyPS5-Source` (`PRIVATE`) excluido; `README.md` actualizado no referencia `Madness Project Nexus` (`~/Escritorio/flash/Madness Project Nexus Classic.swf` descartado; no referenciado en `README.md` actualizado ni en contrato).
- Dependencias: `core/replay.py` usa `json`, `sqlite3`, `hashlib`, `sys`, `os`, `pathlib`, `backends.dispatch`; `tests/` usan `sys.path.insert`; `README.md` describe instalación (`PYTHONPATH=tools`); `tests/` no requieren `requirements.txt` (no existe en candidato ni en repo activo). `README.md` actualizado no menciona `requirements.txt` ni dependencias externas (`rizin` es usado por `backends/dispatch` pero no es obligatorio para `tests/test_integridad_adv_final.py` ni para `core/replay.py` básico; `README.md` no menciona `rizin` como requisito obligatorio para ejecución básica).

## 7. PROCEDIMIENTO DE PUBLICACION RECOMENDADO (reproducible, con verificación)
1. Confirmar que `/tmp/rxre-candidate/` existe y contiene `29` archivos (`find -type f | wc -l`).
2. Confirmar que `README.md` actualizado (`6686` B) no inventa `PROVEN`, describe `PARTIAL` (`F2` pendiente), `C3` pendiente (`PROVEN_ABSENT` sin universo), `READY_NOT_PUBLISHED`, `LICENSE` (`GPL v2`), instalación (`PYTHONPATH=tools`), contrato causal (`docs/CONTRATO_CAUSAL_INV_ESTRING.md`), contrato mínimo F2 (`docs/CONTRATO_F2_W5_MINIMO.md`).
3. Confirmar que `.gitignore` actualizado (`__pycache__`, `rxre.sqlite3`, `.rxre/`, `INFORME_RECUPERACION_RXRE.md`, `KytyPS5-Source`) cubre todos los archivos privados; si falta (`audit/claims.csv` no está en `.gitignore`; debe incluirse si es `RESEARCH_ONLY` o documentarse como `INCLUIR CON NOTA`), actualizar `.gitignore` o `README.md` con nota explícita (`audit/claims.csv` es registro de claims; `scripts/f2_producer_safe.py` requiere `autorización`).
4. Confirmar que `DB` (`rxre.sqlite3`) no está en candidato y `.gitignore` actualizado lo excluye.
5. Confirmar que `tests/` pasan en candidato (`PYTHONPATH=tools` + `python3 -m pytest` o ejecución manual de `test_integridad_adv_final.py`).
6. Confirmar que `README.md` actualizado no contiene referencias a `Madness Project Nexus` o `KytyPS5-Source`; si aparecen, eliminar o documentar como descartados (`README.md` actualizado no las menciona).
7. Confirmar que `docs/INFORME_RXRE_PUB_002.md` (este informe) está presente y documenta `READY_FOR_PUBLICATION_AUTHORIZATION` con `BLOCKED` pendiente `MANUAL_RECONCILIATION_REQUIRED`.
8. Confirmar autorización (`AIRE`: verificar destino exacto `https://github.com/LexLuthorPrimero/rxre`; verificar que no se sobrescriba trabajo remoto (`c682c4a` vacío); verificar que `README.md` actualizado es aceptable para `public`; verificar `.gitignore`; verificar `DB` no publicada; verificar `LICENSE` preservado; verificar evidencia (`e2e_001`..`010`) completa y `hash_sha256` consistente).
9. Confirmar `MERGE_PLAN_READY` (`docs/PLAN_RECONCILIACION_SPE_28.md`): `--allow-unrelated-histories` con verificación `git ls-tree -r --name-only` del `merge` resultante; `README.md` y `LICENSE` preservados; `.gitignore` actualizado aplicado al `merge`; `DB` no incluida en `merge` (`.gitignore` debe funcionar en `merge` también).
10. Confirmar `SPE 29` (`NO_DEFECT_REPRODUCED`): `docs/INFORME_SPE_29.md` documenta que `F2` pendiente (`/dev/mem` pendiente `autorización`); `C3` pendiente (`PROVEN_ABSENT` sin universo); `PROVEN` nunca automático; `e2e_010` (`DATA` confirmada, `CALL` no confirmada, `PARTIAL`); `e2e_009` (`main` `.rodata` `DATA`, `PARTIAL`).
11. Confirmar `MANUAL_RECONCILIATION_REQUIRED` (`docs/RECONCILIACION_LOCAL_REMOTO.md`): `main` remoto (`c682c4a`) vacío; `main` local (`baf2da1`) con `14279` archivos; `merge-base` vacío; `force-push` no autorizado; `README.md` actualizado debe ser verificado antes de `push` o `merge`.
12. Confirmar que `docs/BASELINE_SPE_25.md` está en candidato (`29` archivos incluye `BASELINE_SPE_25.md`, `CONTRATO_CAUSAL_INV_ESTRING.md`, `CONTRATO_F2_W5_MINIMO.md`, `MATRIZ_F2_PRODUCTOR.md`, `INFORME_SPE_29.md`, `INFORME_PUBLICACION_RXRE.md`, `RECONCILIACION_LOCAL_REMOTO.md`, `PLAN_RECONCILIACION_SPE_28.md`).
13. Confirmar que `docs/INFORME_RXRE_PUB_001.md` (`READY_NOT_PUBLISHED`, `MANUAL_RECONCILIATION_REQUIRED`, `READY_FOR_RELEASE_CANDIDATE`) está en candidato o en `docs/` del repo activo (`docs/INFORME_RXRE_PUB_001.md` existe en `docs/`; debe incluirse en candidato o referenciarse en `README.md` actualizado; candidato incluye `docs/INFORME_SPE_29.md` pero no `INFORME_RXRE_PUB_001.md` explícitamente en la lista; debe agregarse o documentarse en `.gitignore`/`README.md`).

Nota de corrección pendiente: `docs/INFORME_RXRE_PUB_001.md` (`SPE 28`) está en `docs/` del repo local pero no copiado explícitamente a `/tmp/rxre-candidate/` en la secuencia anterior (`find /tmp/rxre-candidate/docs/` muestra `BASELINE_SPE_25.md`, `CONTRATO_CAUSAL_INV_ESTRING.md`, `CONTRATO_F2_W5_MINIMO.md`, `MATRIZ_F2_PRODUCTOR.md`, `INFORME_SPE_29.md`, `INFORME_PUBLICACION_RXRE.md`, `RECONCILIACION_LOCAL_REMOTO.md`, `PLAN_RECONCILIACION_SPE_28.md` — `INFORME_RXRE_PUB_001.md` falta). Debe incluirse en candidato o documentarse como pendiente de inclusión. Dado que es `READY_NOT_PUBLISHED`, debe incluirse para transparencia técnica.

## 8. DIFERENCIAS EXACTAS CONTRA GITHUB (`https://github.com/LexLuthorPrimero/rxre`)
- `main` remoto (`c682c4a`): `0` archivos rastreados (`git ls-tree -r --name-only` confirma `0`); `README.md` (`# RXRE...`) accesible (`raw.githubusercontent.com`, `200`); `LICENSE` (`GPL v2`, `1991`) accesible (`raw.githubusercontent.com`, `200`); `.gitignore` (`404` — no existe o no rastreado).
- Candidato (`/tmp/rxre-candidate/`, `29` archivos): `README.md` actualizado (`READY_NOT_PUBLISHED`, `F2` pendiente, `C3` pendiente, contratos, evidencia, instalación `PYTHONPATH=tools`); `LICENSE` (`GPL v2`); `.gitignore` actualizado; `core/` (3 archivos corregidos); `tests/` (11 archivos); `audit/evidence/` (10 archivos); `docs/` (7 archivos incluidos + `INFORME_SPE_29.md` + posible inclusión `INFORME_RXRE_PUB_001.md` pendiente); `scripts/` no copiado (`f2_producer_safe.py` debe incluirse o excluirse explícitamente con nota `RESEARCH_ONLY`).
- Diferencia principal: remoto vacío (`0` rastreados); candidato completo (`29` archivos + posible `scripts/` + posible `INFORME_RXRE_PUB_001.md`). `README.md` actualizado es el cambio más visible; evidencia (`e2e_001`..`010`) es la mayor adición funcional.

## 9. ESTADO FINAL (`READY_FOR_PUBLICATION_AUTHORIZATION` con `BLOCKED` pendiente)
- Candidata (`/tmp/rxre-candidate/`, `29` archivos) verificada; `README.md` actualizado (`6686` B); `LICENSE` (`GPL v2`, `17984` B); `.gitignore` actualizado; evidencia (`e2e_001`..`010`) completa (`10` archivos); `core/` (`3` archivos corregidos); `tests/` (`11` archivos); `docs/` (`7` archivos + `INFORME_SPE_29.md`); `DB` (`rxre.sqlite3`) ausente (`.gitignore` actualizado); `.rxre/gpu0/` ausente (`.gitignore` actualizado); `INFORME_RECUPERACION_RXRE.md` ausente; `KytyPS5-Source` ausente; `audit/claims.csv` no copiado (`debe incluirse o documentarse`); `scripts/f2_producer_safe.py` no copiado (`debe incluirse con nota`); `docs/INFORME_RXRE_PUB_001.md` no copiado (`debe incluirse o documentarse`).
- `READY_FOR_PUBLICATION_AUTHORIZATION`: candidato preparado y verificado (`29` archivos + posible `audit/claims.csv` + posible `scripts/f2_producer_safe.py` + posible `docs/INFORME_RXRE_PUB_001.md`); `README.md` actualizado sin inventos; `LICENSE` preservado; evidencia completa; contrato (`docs/CONTRATO_CAUSAL_INV_ESTRING.md`) preservado; baseline (`docs/BASELINE_SPE_25.md`) preservado; cierre causal (`docs/INFORME_SPE_29.md`) preservado.
- `BLOCKED`: `MANUAL_RECONCILIATION_REQUIRED` (`docs/RECONCILIACION_LOCAL_REMOTO.md`, `docs/PLAN_RECONCILIACION_SPE_28.md`) requiere autorización humana (`git fetch`, `git merge --allow-unrelated-histories` o mecanismo independiente, verificación `git ls-tree -r --name-only` del `merge`, actualización `.gitignore` si falta (`audit/claims.csv`, `scripts/f2_producer_safe.py`, `docs/INFORME_RXRE_PUB_001.md`), confirmación `README.md` actualizado aceptable para `public` (`LexLuthorPrimero`), confirmación `DB` (`rxre.sqlite3`) no incluida en `push` o `merge` (`.gitignore` actualizado debe funcionar en `merge`), confirmación `evidence` (`e2e_001`..`010`) completa, confirmación `tests/` pasan (`PYTHONPATH=tools`), confirmación `F2` (`/dev/mem`) pendiente (`docs/CONTRATO_F2_W5_MINIMO.md`, `docs/MATRIZ_F2_PRODUCTOR.md`, `docs/INFORME_SPE_29.md`), confirmación `C3` (`PROVEN_ABSENT`) pendiente (`docs/CONTRATO_CAUSAL_INV_ESTRING.md`, `docs/BASELINE_SPE_25.md`), confirmación `PROVEN` nunca automático (`docs/BASELINE_SPE_25.md`, `docs/INFORME_SPE_29.md`)).
- `READY_NOT_PUBLISHED`: `docs/INFORME_PUBLICACION_RXRE.md` (`SPE 26`) confirma que no se hizo `push`; `SPE 28` (`READY_NOT_PUBLISHED`) confirma `READY_NOT_PUBLISHED`; `SPE 29` (`NO_DEFECT_REPRODUCED`) confirma que no hay defecto que impida la publicación; `SPE 27` (`MANUAL_RECONCILIATION_REQUIRED`) confirma historia divergente; `SPE 28` (`MERGE_PLAN_READY`) confirma que la reconciliación es posible con autorización; `SPE 29` confirma que el flujo causal está completo y verificado; la única barrera es la reconciliación (`MANUAL_RECONCILIATION_REQUIRED`) y la autorización para `push`/`merge` (`AIRE` requiere verificación exacta del destino, verificación de contenido revisado, verificación de ausencia de secretos, verificación de integridad de historia publicada, verificación de `DB` no publicada).
- `MADNESS PROJECT NEXUS CLASSIC`: `~/Escritorio/flash/Madness Project Nexus Classic.swf` descartado (`SPE 29` confirma que no es requisito ni bloqueo; `README.md` actualizado no lo menciona; `docs/INFORME_SPE_29.md` confirma que no se analizó ni ejecutó). No debe reaparecer como requisito.

## 10. SIGUIENTE ACCION (una sola, de mayor valor)
Confirmar con usuario (`LexLuthorPrimero`) que `MANUAL_RECONCILIATION_REQUIRED` (`docs/RECONCILIACION_LOCAL_REMOTO.md`, `docs/PLAN_RECONCILIACION_SPE_28.md`) está autorizada (`git fetch https://github.com/LexLuthorPrimero/rxre`, `git merge --allow-unrelated-histories c682c4a` con verificación `git ls-tree -r --name-only` del `merge`, actualización `.gitignore` para incluir `audit/claims.csv` y `scripts/f2_producer_safe.py` si se incluyen, actualización `README.md` si se requiere ajuste menor tras `merge`, verificación `tests/` (`PYTHONPATH=tools`) tras `merge`, confirmación `DB` no incluida en `push` o `merge` (`.gitignore` actualizado debe funcionar en `merge`), confirmación `evidence` (`e2e_001`..`010`) completa en `merge`, confirmación `core/` corregido (`VALID_EPISTEMIC` actualizado) en `merge`, confirmación `tests/` (`test_integridad_adv_final.py` 8/8 PASS) tras `merge`, confirmación `docs/` (`BASELINE_SPE_25.md`, contratos, informes) preservados en `merge`, confirmación `LICENSE` (`GPL v2`) preservado, confirmación `README.md` actualizado (`READY_NOT_PUBLISHED`, `F2` pendiente, `C3` pendiente, contratos, evidencia, instalación) aceptable para `public`).

Si no se autoriza la reconciliación (`MANUAL_RECONCILIATION_REQUIRED` bloquea `push`), el proyecto permanece `READY_NOT_PUBLISHED` con candidato (`/tmp/rxre-candidate/`) verificado y preparado, sin modificaciones al repositorio activo ni al remoto, con límite `BLOCKED` documentado (`MANUAL_RECONCILIATION_REQUIRED` pendiente autorización).
