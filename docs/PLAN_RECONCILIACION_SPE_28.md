# PLAN DE RECONCILIACION NO DESTRUCTIVA — SPE 28
Estado final: `MERGE_PLAN_READY`
Fecha: 2026-10-18. Proyecto: `/home/lucas/Escritorio/rxre`. Usuario: `LexLuthorPrimero`.

## 1. OBJETOS VERIFICADOS (no asumidos)

| OBJETO | LOCAL / REMOTO | SHA / REF | EVIDENCIA | DECISION |
|---|---|---|---|---|
| `HEAD` (`main`) | Local (`main`) | `baf2da15185017907bfa2ad219032e6fe97388fa` | `rev-parse --verify HEAD` confirma `commit` | Base de la historia local completa (`14279` archivos en árbol) |
| `baf2da1` | Local (`main`) | Igual a `HEAD` | Confirmado; `ls-tree -r` muestra contenido completo | No hay divergencia interna; es la historia de trabajo |
| `c682c4a` (remoto `main`) | Remoto (`public`) | `c682c4a4cf4e2c5c518a90f41e54107a7ecde6db` | `git ls-remote` confirma; `rev-parse` confirma local; `ls-tree -r` confirma `0` archivos rastreados; `README.md` (`# RXRE...`) y `LICENSE` (GPL v2) accesibles vía `raw.githubusercontent.com` | Remoto es un repositorio esencialmente vacío (o con archivos no rastreados en el objeto `c682c4a`); no hay conflicto de contenido, solo historia independiente |
| `merge-base` `baf2da1` vs `c682c4a` | No existe | Vacío (`merge-base` vacío) | `git merge-base` confirma `0` ancestro común | Divergencia de historia confirmada; no se puede hacer `push` normal (`non-fast-forward`) sin `force` |
| `legacy` (remoto histórico) | `/home/lucas/Escritorio/RX550-INVESTIGACION` | `push`/`fetch` local | `remote -v` confirma | `CONSERVAR`: nunca usar para publicación pública; solo referencia histórica |

## 2. ARCHIVOS RELEVANTES DEL REMOTO (verificados sin exposición de secretos)
- `README.md`: accesible (`https://raw.githubusercontent.com/LexLuthorPrimero/rxre/main/README.md`); contenido: descripción del proyecto (`# RXRE — Reverse Engineering Engine`, validación con RX 550 / Linux 7.1.3, no límite arquitectónico, flujo JSON Lines).
- `LICENSE`: accesible (`GPL v2`, `1991`); debe preservarse en cualquier reconciliación.
- `.gitignore`: `404` (no existe en remoto o no está rastreado en `c682c4a`).
- `c682c4a` (objeto `commit`): `0` archivos rastreados (`git ls-tree -r --name-only` confirma). Esto implica que `README.md` y `LICENSE` pueden no estar en el árbol del commit `c682c4a`, sino en una referencia de rama diferente o en un objeto no rastreado; en cualquier caso, el contenido remoto visible es mínimo y no conflictivo con el contenido local.

## 3. ARCHIVOS LOCALES QUE DEBEN CONSERVARSE (sin exclusión sin autorización)
- `audit/evidence/e2e_001.json` a `e2e_010.json`: evidencia estructural (`VALID`), dinámica (`PARTIAL`), cruzada (`VALID`), independiente (`VALID`), frontera (`PARTIAL`). No contienen secretos; `hash_sha256` verificado contra artefactos (`amdgpu.ko`: `53f55...`; `/bin/ls`: `54e93...`; `rxre_min.elf`: `a183f...`).
- `docs/BASELINE_SPE_25.md`: baseline técnico (matriz de capacidades, defectos corregidos, límites explícitos).
- `docs/INFORME_PUBLICACION_RXRE.md`: informe de publicación controlada (`READY_NOT_PUBLISHED`).
- `docs/RECONCILIACION_LOCAL_REMOTO.md`: informe de reconciliación (`MANUAL_RECONCILIATION_REQUIRED`).
- `docs/RECONCILIACION_LOCAL_REMOTO.md` (este informe): reemplaza el anterior como `PLAN_RECONCILIACION_SPE_28.md` (nuevo archivo); los anteriores no se sobrescriben.
- `core/evidence_integrity.py`: corregido (`VALID_EPISTEMIC` actualizado con `"VALID"`); `accept_evidence` funciona.
- `core/replay.py`: `evaluate_contract`, `replay_operacion`, `verify_reinvestigation`, `plan_reinvestigation`, `analyze_dependencies` integrados.
- `core/orchestrator.py`: `Orchestrator.run()` con `dry_run`; flujo completo.
- `tests/*.py`: adversariales (`8/8 PASS`), contrato uniforme (`5/5 PASS`), reproducibilidad (`2/2 PASS`), estructura independiente (`PASS`), dinámica segura (`PASS`), semántica estructural (`PASS`).
- `.rxre/gpu0/original` (4096B), `restaurado`, `snapshot_meta.json`: fixtures internos del contrato F2; deben conservarse pero no publicarse sin revisión explícita (pueden contener referencias locales a DB).
- `audit/claims.csv`: rastreado (`M`); debe preservarse como registro de claims.

## 4. DIFERENCIAS Y CONFLICTOS POTENCIALES (no ejecutados)
- `README.md` remoto (`public`) vs ausencia en `HEAD` local: si se hace reconciliación con `--allow-unrelated-histories`, `README.md` remoto se preservará automáticamente si se fusionan los árboles; si se reemplaza el árbol (`push --force`), `README.md` remoto se perdería a menos que se copie explícitamente al árbol local primero.
- `LICENSE` remoto (`GPL v2`) vs `LICENSE` local: no hay `LICENSE` local (`ls` confirma ausencia en raíz de `baf2da1`); debe incluirse en cualquier publicación para preservar licencia.
- `.gitignore`: remoto no tiene `.gitignore`; local tiene `.gitignore` parcial (`__pycache__/`); no hay conflicto, solo diferencia de política de exclusión.
- `DB` (`rxre.sqlite3`): local (`3665920` bytes); remoto (`0` archivos rastreados, por lo que `DB` no está en remoto); no hay conflicto de contenido porque `DB` no se publica (debe mantenerse privada o documentada como archivo local no rastreado en `.gitignore`).
- `audit/evidence/e2e_001`..`010`: nuevos; no hay conflicto con remoto vacío; son archivos que deben publicarse si se decide transparencia completa.
- `docs/BASELINE_SPE_25.md`, `docs/INFORME_PUBLICACION_RXRE.md`, `docs/RECONCILIACION_LOCAL_REMOTO.md`: nuevos; deben incluirse como referencia técnica; no hay conflicto.
- `tests/*.py`: nuevos; no hay conflicto con remoto vacío; son parte esencial del proyecto.
- `.rxre/gpu0/` (fixture interno): debe ser documentado como interno; si se publica, debe ir acompañado de nota en `README.md` o `.gitignore` actualizado.

## 5. EVALUACION DE ALTERNATIVAS (no ejecutadas)

### A. Fusionar con `--allow-unrelated-histories`
- Operaciones propuestas (no ejecutadas): `git fetch https://github.com/LexLuthorPrimero/rxre`, `git checkout -b reconcile` (opcional, no obligatorio), `git merge --allow-unrelated-histories c682c4a4cf4e2c5c518a90f41e54107a7ecde6db`.
- Preservación: ambas historias (`baf2da1` y `c682c4a`) se preservan en el grafo; el `merge-base` vacío se convierte en un `merge commit` con dos padres; `HEAD` local (`baf2da1`) y remoto (`c682c4a`) coexisten.
- Conflictos: `README.md` y `LICENSE` remotos se fusionan automáticamente con el árbol local (porque `baf2da1` no tiene `README.md` ni `LICENSE` en raíz); no hay conflicto de archivo porque los archivos remotos son nuevos para `baf2da1`.
- Riesgos: `c682c4a` tiene `0` archivos rastreados; si `README.md` y `LICENSE` no están en `c682c4a` (aunque accesibles vía `raw.githubusercontent.com`), `merge` podría no incluirlos; debe verificarse con `git ls-tree` del `merge` resultante.
- Verificación: `git ls-tree -r --name-only` del `merge commit` debe incluir todos los archivos locales (`14279`) más `README.md` y `LICENSE` (si existen en `c682c4a` o si se agregan manualmente antes del `merge`).
- Condición de detención: si `README.md` o `LICENSE` remotos contienen contenido que contradice el contrato (`PROVEN` inventado, resultados falsos), debe detenerse antes del `merge` y corregir manualmente.

### B. Incorporar archivos remotos controladamente (sin `merge` de historia)
- Operaciones propuestas: `git checkout c682c4a4cf4e2c5c518a90f41e54107a7ecde6db -- README.md LICENSE` (solo lectura, no modifica historia); luego `git add`, `git commit` (nuevo `commit` con `baf2da1` como padre, incluyendo archivos remotos). Esto crea un `commit` descendiente de `baf2da1` que incorpora los archivos remotos, sin `merge`.
- Preservación: `c682c4a` no se modifica; `baf2da1` sigue siendo ancestro; `README.md` y `LICENSE` se agregan a la historia local; `push` sería `fast-forward` respecto a `baf2da1`, pero `non-fast-forward` respecto a `c682c4a` (porque `baf2da1` no desciende de `c682c4a`). Por lo tanto, `push` normal seguiría siendo rechazado; se requiere `force-push` para reemplazar `main` remoto con la historia extendida.
- Conflictos: `README.md` remoto (`# RXRE...`) debe actualizarse para reflejar el estado actual (`PARTIAL`, `VALID_EPISTEMIC` corregido, `e2e_010`, `F2` pendiente); `LICENSE` debe preservarse (`GPL v2`).
- Riesgos: `force-push` sobrescribe `main` remoto; requiere autorización explícita; debe verificarse que `README.md` actualizado no invente `PROVEN` ni resultados falsos.
- Verificación: `git diff baf2da1..nuevo_commit` debe mostrar solo `README.md` (actualizado) y `LICENSE` (agregado), sin eliminación de archivos locales ni cambios en evidencia, DB o fixtures internos.

### C. Mantener remoto actual y preparar publicación posterior por mecanismo independiente
- Operaciones propuestas: no modificar `main`; crear una nueva rama (`rxre-baseline`) a partir de `baf2da1`; hacer `push --force-with-lease` de `rxre-baseline` al remoto como `main` (requiere autorización); o crear un repositorio nuevo (`rxre-public-v2`) con `baf2da1` como primer `commit`.
- Preservación: `main` remoto (`c682c4a`) no se modifica hasta que se autorice; `baf2da1` se preserva completamente.
- Conflictos: `README.md` y `LICENSE` remotos deben incluirse en el nuevo `commit` inicial para preservar licencia y documentación básica.
- Riesgos: crear un nuevo repositorio (`rxre-public-v2`) podría duplicar el proyecto; debe documentarse que el repositorio original (`rxre`) sigue siendo el de referencia hasta que se confirme la migración.
- Verificación: `git ls-tree -r --name-only` del `commit` inicial del nuevo repositorio debe incluir todos los archivos locales (`14279`) más `README.md` actualizado y `LICENSE` (`GPL v2`).

## 6. SECUENCIA PROPUESTA (no ejecutada)
- No hay `force-push` predeterminado; no hay `merge` automático.
- Paso 1 (verificación): confirmar que `README.md` remoto (`raw.githubusercontent.com`) contiene solo descripción (`# RXRE...`, validación con RX 550, flujo JSON Lines) sin resultados inventados ni `PROVEN` automático; confirmar que `LICENSE` es `GPL v2` (`1991`).
- Paso 2 (preservación): `git ls-remote` confirma `main` (`c682c4a`); `git rev-parse` confirma `baf2da1` (`HEAD`); `git ls-tree` confirma `0` archivos en `c682c4a` (`14279` en `baf2da1`).
- Paso 3 (decisión humana): si `README.md` remoto está libre de inventos (`PROVEN` automático, resultados falsos), entonces la reconciliación es segura; de lo contrario, detener y corregir `README.md` antes de cualquier `merge` o `push`.
- Paso 4 (plan recomendado): usar alternativa `A` (`--allow-unrelated-histories`) con verificación posterior del árbol (`git ls-tree -r --name-only` del `merge commit`) para confirmar que `README.md` y `LICENSE` se preservan; luego `git push` normal (porque `merge commit` tendrá `c682c4a` como padre, haciendo que `main` remoto avance con `fast-forward` si `c682c4a` es ancestro del `merge commit`).
- Paso 5 (autorización): antes de cualquier `push`, confirmar con usuario que `README.md` actualizado (`docs/BASELINE_SPE_25.md` + `docs/INFORME_PUBLICACION_RXRE.md` + `docs/RECONCILIACION_LOCAL_REMOTO.md` + `e2e_010` + `VALID_EPISTEMIC` corregido) es aceptable para publicación pública; confirmar que no hay datos sensibles (`.rxre/gpu0/` debe documentarse como interno o excluirse con `.gitignore` actualizado).
- Paso 6 (ejecución futura, no realizada en esta misión): si se autoriza, ejecutar `git fetch`, `git checkout -b reconcile`, `git merge --allow-unrelated-histories c682c4a4cf4e2c5c518a90f41e54107a7ecde6db`, verificar `README.md` y `LICENSE` en `git ls-tree`, actualizar `.gitignore` para `.rxre/gpu0/`, actualizar `README.md`, y solo entonces `git push` (o `force-push` si `main` remoto debe reemplazarse, con autorización explícita).

## 7. PRUEBAS DE ACEPTACION (para ejecución futura, no ejecutada)
- `test_integridad_adv_final.py` (8/8 PASS) debe pasar antes y después de la reconciliación (`repo` y `/tmp`).
- `test_contrato_uniforme.py` (5/5 PASS) debe pasar.
- `test_reproducibilidad_end2end.py` (2/2 PASS) debe pasar.
- `git ls-tree -r --name-only` debe incluir `README.md` (`actualizado`), `LICENSE` (`GPL v2`), todos los archivos locales (`14279`) y `.gitignore` actualizado (`.rxre/gpu0/` documentado o excluido).
- `git rev-parse --verify HEAD` debe ser un `commit` con al menos dos padres (`baf2da1` y `c682c4a`), confirmando que ambas historias se preservan.
- No debe haber nuevos archivos no rastreados que no estén documentados (`.rxre/gpu0/` debe ser explícito en `.gitignore` o `README.md`).

## 8. RIESGOS RESIDUALES
- `c682c4a` es un `commit` con `0` archivos rastreados (`ls-tree` confirma); `README.md` y `LICENSE` accesibles vía `raw.githubusercontent.com` pueden no ser parte del árbol de `c682c4a`, sino solo archivos mostrados por GitHub en la interfaz. Si se hace `merge --allow-unrelated-histories` y `README.md` no está en `c682c4a`, el `merge` no incluirá `README.md` automáticamente; debe verificarse con `git ls-tree` del `merge` resultante.
- `force-push` sobrescribe `main` remoto sin posibilidad de recuperación (`c682c4a` se pierde como `main` a menos que se preserve en otra rama). Si se usa `--allow-unrelated-histories`, `c682c4a` se preserva como ancestro del `merge commit`; no se requiere `force-push`.
- `.rxre/gpu0/` (fixture interno) no debe publicarse sin nota; `DB` (`rxre.sqlite3`) debe mantenerse privada (no debe incluirse en el `push`).
- `docs/BASELINE_SPE_25.md`, `docs/INFORME_PUBLICACION_RXRE.md`, `docs/RECONCILIACION_LOCAL_REMOTO.md` (y `docs/PLAN_RECONCILIACION_SPE_28.md`, este informe) deben incluirse para transparencia técnica, pero deben documentar que `F2` (`/dev/mem`) está pendiente y que `C3` (`PROVEN_ABSENT`) no se ha asignado.

## 9. DECISION HUMANA REQUERIDA (punto exacto de autorización)
- Antes de cualquier `push` o `merge` real, el usuario (`LexLuthorPrimero`) debe confirmar:
  1. Que `README.md` actualizado (`docs/BASELINE_SPE_25.md` + `docs/INFORME_PUBLICACION_RXRE.md` + `e2e_010` + `VALID_EPISTEMIC` corregido) es aceptable para publicación pública (`public` en `LexLuthorPrimero/rxre`).
  2. Que `LICENSE` (`GPL v2`) debe preservarse (`README.md` remoto ya lo indica).
  3. Que `.rxre/gpu0/` debe documentarse como archivo interno (`README.md` actualizado debe incluir nota o `.gitignore` actualizado debe excluirlo explícitamente).
  4. Que `DB` (`rxre.sqlite3`) debe mantenerse privada (no debe incluirse en `.gitignore` como exclusión obligatoria, pero debe documentarse que no se publica).
  5. Que no hay `force-push` autorizado sin verificación previa del `diff` (`git diff baf2da1..merge_commit` debe confirmar que solo se agregan archivos locales y `README.md`/`LICENSE`, sin eliminación ni modificación destructiva).
- Si alguna de estas confirmaciones falla (`README.md` con inventos de `PROVEN`, `DB` expuesta, `.gitignore` incompleto sin documentación), la reconciliación debe detenerse (`BLOCKED_WITH_EVIDENCE`) hasta corregir el defecto.

## 10. CONCLUSION (sin ejecución de operación)
- `MERGE_PLAN_READY`: el plan no destructivo está respaldado por evidencia (`HEAD` `baf2da1`, `c682c4a` vacío, `merge-base` vacío, `README.md` y `LICENSE` verificados, `DB` intacta, evidencia completa, `core/` corregido, `tests` 8/8 PASS).
- No se ejecutó `git merge`, `git commit`, `git push`, `git reset`, `git clean`, `git restore`, `git checkout`, `git stash`, `force-push`, creación de ramas ni worktrees.
- No se inició `SPE 28` como desarrollo funcional nuevo (`F2` físico pendiente); se completó como fase de planificación técnica con `docs/PLAN_RECONCILIACION_SPE_28.md` creado sin sobrescribir informes previos.
- Proyecto completo con evidencia (`e2e_001`..`010`), contrato (`evaluate_contract`), flujo (`Orchestrator`), baseline (`docs/BASELINE_SPE_25.md`), publicación (`docs/INFORME_PUBLICACION_RXRE.md`), reconciliación (`docs/RECONCILIACION_LOCAL_REMOTO.md`), y plan (`docs/PLAN_RECONCILIACION_SPE_28.md`).
