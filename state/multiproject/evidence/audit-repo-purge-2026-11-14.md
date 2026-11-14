# Auditoría y purga del repo LexLuthorPrimero/rxre — EJECUTADA 2026-11-14

Decisión del propietario (sesiones 2026-11-14): Tier 1 borrar, Tier 2 borrar, Tier 3 borrar (root sueltos), purga con force push.

Contenido eliminado de todo el historial (filter-branch --index-filter sobre refs/heads/* y tags):
- RESEARCH/working (Linux 7.1.3: headers AMD_sh_mask.h + fuente amdgpu DRM; ~539 MB)
- RESEARCH/kernelbuild (árbol Linux 7.1.3 + .config + outputs; ~64 MB)
- RESEARCH/GAME-001 (corpus .swf; 3333 archivos)
- benchmark/ (dogfood/migraciones; 138 archivos, ~41 MB)
- amdgpu.ko (34 MB), gitlink KytyPS5-Source, 04-IMPLEMENTACION/rx550-driver/*.cmd
- 96 sueltos del root (informes/diálogos/métricas, incl. METRICAS_R3.md); estructurales conservados.

Verificación post-purga: `git rev-list --objects --all | grep -E 'paths purgadas'` = 0 en todos los refs; `git fsck --strict` sin salida; pack 480 MiB → 150 MiB; tag v1.0-fase2-completa intacta y sin contenido purgado.

Force push: main bf1c9903... → 71b37f1e (refs/heads/rewrite/main, lease). GitHub: único branch sigue siendo main; sin tags. Objetos huérfanos persistirán server-side hasta GC de GitHub.

Backup completo: /home/lucas/rxre-backup-2026-11-14.bundle (499 MB, incluye todo el historial removido).
