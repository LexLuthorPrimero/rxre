# Auditoría del repo LexLuthorPrimero/rxre — 2026-11-14

Método: `git ls-files -s` + `git cat-file --batch-check` (tamaños reales de blobs en HEAD), `git count-objects -vH`, análisis por extensión y por directorio. Total tracked: **24,039 archivos, 728.4 MB en blobs** (pack en disco: 480 MiB). HEAD descompone en:

## Por directorio (top)

| Dir | MB | Archivos | Naturaleza |
|---|---:|---:|---|
| RESEARCH/working | 538.5 | 2,787 | headers AMD `_sh_mask.h` + fuente amdgpu DRM (upstream Linux 7.1.3) |
| RESEARCH/kernelbuild | 64.1 | 16,587 | árbol Linux 7.1.3 completo + `.config` + outputs de build (.cmd/.o/.ko) |
| benchmark/ | 40.8 | 138 | corpus/dogfood de sesiones (regex-t5, swf-nexus-classic, REPO-MIGRATION-003…) |
| amdgpu.ko | 34.0 | 1 | módulo kernel compilado |
| rxre-r3/ | 14.8 | 161 | evidencia RXRE R3 (reconstrucciones wc/filenvercmp, oráculos, sellos) — **referenciado públicamente** |
| tools/ | 5.0 | 357 | engine RXRE (migraciones, backends, tests) — core |
| audit/ | 3.0 | 78 | auditorías |
| RXRE_PLAN_MAESTRO.md | 1.7 | 1 | documento largo de planificación |
| KytyPS5-Source | 0 (gitlink) | 1 | gitlink colgante, SIN .gitmodules; ignorado en .gitignore |
| resto | ~4 | ~3,400 | docs, research notes, informes sueltos |

Por extensión: `.h` 554 MB (8,381 uds, casi todo kernel AMD), `.swf` 45 MB (3,335 uds, RESEARCH/GAME-001/assets), `.c` 33 MB, `.json` 12 MB, `.o` 11 MB, `.txt` 8 MB.

## Tiers propuestos

**Tier 1 — artefactos/upstream vendored, no son obra propia (≈612 MB, ~19,400 archivos):**
- `RESEARCH/working/` completo (headers AMD + fonte amdgpu DRM de Linux 7.1.3)
- `RESEARCH/kernelbuild/` completo (árbol Linux + build outputs; 190 de los 24039 son .o/.ko/.cmd/.symvers)
- `amdgpu.ko` (módulo compilado)
- gitlink `KytyPS5-Source` (colgante; el directorio local NO se toca, queda ignorado)

**Tier 2 — corpus de investigación (¿eliminable? no es obra propia pero es evidencia potencial):**
- `RESEARCH/GAME-001/assets/*.swf` (3,333 archivos, 9.1 MB) — corpus de análisis SWF de un juego comercial (análisis propio: 16 MB totales)
- `benchmark/` (138 archivos, 40.8 MB) — dogfood/migraciones/auditorías de sesiones
- `rx550-upstream-7.2.8/` (0.8 MB)
- `01-*? (06-INGENIERIA-INVERSA, 04-IMPLEMENTACION, 03-EXPERIMENTOS, 07-DRIVER, 08-ARQUITECTURA)` — código/docs propios de RXRE: MANTENER

**Tier 3 — sueltos del root (109 archivos, ~5 MB):** informes de sesiones, diálogos, métricas (`METRICAS_R3.md`), reportes V5/V6/V9. No miden funcionalidad; es memoria operativa. Opciones: borrar, mover a `archive/` (conservar), o dejar.

**Tags**: `v1.0-fase2-completa` existe — una reescritura de historia lo rompe.

## Purga de historia (opción separada)

`git rm` reduce HEAD pero el pack (480 MB) queda en historia y GitHub sigue sirviendo esos blobs en commits anteriores. Purga real = `git filter-repo --invert-paths --path ...` + **force push** + reubicación del tag — reescritura completa de hashes. No recomendado sin dictado explícito.
