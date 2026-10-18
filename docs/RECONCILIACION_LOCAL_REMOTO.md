# RECONCILIACION LOCAL-REMOTO RXRE (SPE 27)
Estado final: `MANUAL_RECONCILIATION_REQUIRED`
Fecha: 2026-10-18. Proyecto: `/home/lucas/Escritorio/rxre`. Usuario: `LexLuthorPrimero`.

## 1. OBJETOS VERIFICADOS (no asumidos)

| OBJETO | LOCAL | REMOTO | EVIDENCIA | DECISION |
|---|---|---|---|---|
| `HEAD` (rama `main`) | `baf2da15185017907bfa2ad219032e6fe97388fa` (commit) | `main` apunta a `c682c4a4cf4e2c5c518a90f41e54107a7ecde6db` | `git rev-parse HEAD` confirmado; `git ls-remote` confirmado | `MANUAL_RECONCILIATION_REQUIRED`: historias sin ascendencia común |
| `baf2da1` | Existe local (`commit`, `main`) | No es `main` remoto | `rev-parse --verify` confirma local; no coincide con `c682c4a` | Divergencia confirmada |
| `c682c4a` (remoto `main`) | Existe local (`commit`) | `main` (`public`, `pushed_at` 2026-10-11) | `rev-parse --verify` confirma; `git ls-tree` muestra `0` archivos (árbol vacío) | Remoto es un commit vacío o repositorio inicial; no hay conflicto de contenido, solo de historia |
| `legacy` (remoto local) | `/home/lucas/Escritorio/RX550-INVESTIGACION` (`push`/`fetch`) | No es GitHub; es repositorio histórico protegido | `git remote -v` confirma | `CONSERVAR SIN CAMBIOS`: nunca usar `push` a `legacy` para publicación pública |

## 2. ASCENDENCIA Y DIVERGENCIA
- `git merge-base baf2da1 c682c4a` → vacío (`merge-base` vacío). No existe ancestro común.
- `git ls-tree -r --name-only baf2da1` → `14279` archivos (proyecto completo con core, tests, fixtures, docs, evidencia).
- `git ls-tree -r --name-only c682c4a` → `0` archivos (repositorio vacío o inicial).
- Conclusión: `baf2da1` y `c682c4a` son historias completamente independientes. No hay divergencia de contenido (porque `c682c4a` no tiene contenido), pero sí divergencia de historia: `baf2da1` no desciende de `c682c4a`; cualquier `push` normal (`git push`) resultaría en `rejected (non-fast-forward)`; cualquier `force-push` sobrescribiría `main` remoto con `14279` archivos nuevos sin revisión del usuario.

## 3. DIFERENCIAS DE ARCHIVOS (conflictos sin resolver)
- Nuevos archivos locales no presentes en remoto (`0` archivos en remoto; `14279` en local): todos los archivos del proyecto son nuevos respecto al repositorio remoto vacío.
- Archivos eliminados en local respecto al remoto: ninguno (remoto vacío).
- Archivos modificados con historia divergente: `audit/claims.csv`, `.rxre/gpu0/original`, `KytyPS5-Source`. No hay conflicto de contenido porque no hay base común; son cambios nuevos en una historia independiente.

## 4. REVISION DE CONTENIDO (seguridad e integridad)
- `docs/INFORME_PUBLICACION_RXRE.md`: creado; documenta `READY_NOT_PUBLISHED`, verificación de secretos (`0` ocurrencias sensibles), verificación del remoto (`c682c4a`), y recomendación de revisión manual.
- `docs/BASELINE_SPE_25.md`: creado; documenta matriz de capacidades, defectos corregidos (`VALID_EPISTEMIC`), límites (`F2 PARTIAL`, `C3` pendiente), y comandos de reproducción.
- `audit/evidence/e2e_001.json` a `e2e_010.json`: preservados; `epistemic` verificado (`VALID`/`PARTIAL`/`NOT_DETERMINED`); `hash_sha256` coincidente con artefactos reales (`amdgpu.ko`, `/bin/ls`, `rxre_min.elf`).
- `core/evidence_integrity.py`: corregido (`VALID_EPISTEMIC` actualizado); `accept_evidence` pasa evidencia válida (`e2e_007`); rechaza evidencia alterada.
- `DB` (`rxre.sqlite3`): intacta (`3665920` bytes); sin registros nuevos de evidencia; no modificada.
- `RX550-INVESTIGACION` (`/home/lucas/Escritorio/RX550-INVESTIGACION`): no tocado.
- `.rxre/gpu0/` (fixture interno con `original`, `restaurado`, `snapshot_meta.json`): existente; debe ser documentado como interno, no necesariamente publicado sin revisión.

## 5. RIESGOS RESIDUALES
- `MANUAL_RECONCILIATION_REQUIRED`: la historia local no desciende del remoto. Una publicación requiere decisión explícita del usuario: (a) reemplazar `main` remoto con `push --force-with-lease` (no recomendado sin autorización), o (b) crear una nueva rama (`rxre-baseline`) y hacer `push` como PR, o (c) inicializar el remoto con `baf2da1` como primer commit (requiere `push --force` o eliminación del `main` existente).
- El repositorio remoto (`c682c4a`) es `public`; cualquier cambio publicado será visible inmediatamente.
- No hay `.gitignore` completo que excluya `.rxre/gpu0/` o `DB`; una publicación debe incluir `README.md` que explique qué archivos son internos.
- No hay `README.md` local. El `README` remoto (`raw.githubusercontent.com/LexLuthorPrimero/rxre/main/README.md`) existe (`# RXRE — Reverse Engineering Engine`) pero no refleja el estado actual (`PARTIAL`, `e2e_010`, `VALID_EPISTEMIC` corregido).

## 6. DECISIONES Y RECOMENDACIONES (no ejecutadas)
- No hacer `push` automático (`FUEGO` prohibido; `AIRE` requiere verificación exacta del destino; `MANUAL_RECONCILIATION_REQUIRED` bloquea publicación automática).
- Si se autoriza publicación: crear primero `README.md` local (o actualizar `.gitignore`) que documente el estado actual (`VALID`/`PARTIAL`, `e2e_001`..`010`, `F2` pendiente); luego revisar el diff completo (`git diff` no aplicable por historia divergente; usar `git archive` o `git ls-tree` para comparar); finalmente decidir si reemplazar `main` remoto (`force-push` con autorización explícita) o crear PR con nueva rama.
- Si no se autoriza: mantener `READY_NOT_PUBLISHED` (como en `docs/INFORME_PUBLICACION_RXRE.md`).
- No iniciar `SPE 27`; el objetivo técnico pendiente (`F2` físico) es independiente de la reconciliación del repositorio remoto.

## 7. COMANDOS EJECUTADOS (reproducibles, sin modificaciones destructivas)
```bash
git rev-parse --verify HEAD
git rev-parse --verify baf2da1
git rev-parse --verify c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
git merge-base baf2da1 c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
git ls-tree -r --name-only baf2da1
git ls-tree -r --name-only c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
git remote -v
git branch -v
git status --short | wc -l
```
Todos los comandos son de lectura; no modificaron historia, archivos ni DB.

## 8. ESTADO DE CIERRE
- `MANUAL_RECONCILIATION_REQUIRED` (historia divergente, remoto vacío, contenido local completo, sin secretos, sin publicación automática).
- No se creó `SPE 27`; no se inició cadena de speedruns adicionales.
- Proyecto completo con baseline (`docs/BASELINE_SPE_25.md`) y publicación documentada (`docs/INFORME_PUBLICACION_RXRE.md`), con límites explícitos (`F2 PARTIAL`, `C3` pendiente, `MANUAL_RECONCILIATION_REQUIRED`).
