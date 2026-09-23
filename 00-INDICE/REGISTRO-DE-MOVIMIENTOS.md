# REGISTRO-DE-MOVIMIENTOS.md — Trazabilidad de la reorganización documental

> Cada movimiento de la reorganización se registra aquí con: `origen → destino → hash → fecha → motivo`.
> Los hashes pre-movimiento están en `REORGANIZACION-MANIFEST.sha256` (1.645 entradas: 1.257 del repo histórico + 388 de power-sweep home; los 6 de `RX550_Benchmarks` se verificaron pre/post en el grupo 05).
> Autorización: "GO" del usuario (2026-09-23) — ejecución exacta según PLAN DE EJECUCIÓN, incluidas las 5 asignaciones puntuales confirmadas.

| # | Origen (ruta) | Destino (ruta) | Fecha | Hash verificado | Motivo |
|---|---|---|---|---|---|
| 1 | `RX550_Iterative_Research/experiments/FASE-R2-PROJECT-DOCUMENTATION/` — 14 diseños FASE-E…Q + EXPERIMENT-PRIORITY-MATRIX + SYNTHETIC-WORKLOAD-DESIGN | `04-IMPLEMENTACION/` (14) + `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` (1) | 2026-09-23 | 15/15 SHA256 pre/post idénticos | Asignaciones puntuales 1–3 aprobadas en el GO: diseños y mapa global |
| 2 | Docs raíz del repo histórico (8): `MASTER-PLAN.md`, `MASTER-RESEARCH-STATUS.md`, `FINAL-RESEARCH-STATUS.md`, `PROJECT-DOCUMENTATION-STATUS.md`, `README.md`, `decisions.md`, `REORGANIZATION-AUDIT.md`, `experiments_proposed.md` | `00-INDICE/` | 2026-09-23 | 8/8 SHA256 pre/post idénticos | Asignaciones puntuales 4–5: auditoría y propuestas → índice |
| 3 | `experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/`, `FASE-R2-PROJECT-DOCUMENTATION/` (resto: 3), `FASE-R3-NOVELTY-AUDIT/`, `FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/`, `AUDIT-001/`, `IMPLEMENTATION-READINESS/` | `01-AUDITORIA/` | 2026-09-23 | 37/37 idénticos (pre/post grupo + manifest) | Auditorías documentales con rol definido |
| 4 | `experiments/POLARIS12-MAP/` (5), `RX550_BUILD_SPECIFICATION.txt` (1), `knowledge.md`+`evidence.md`+`hypotheses.md`+`open_questions.md`+`rejected_ideas.md`+`research_log.md` (6) | `02-ARQUITECTURA/` | 2026-09-23 | 12/12 idénticos (pre/post grupo + manifest) | Conocimiento acumulado y especificación de arquitectura |
| 5 | `experiments/FASE-R4A-BANDWIDTH-REAL/`, `FASE-R4B-GOVERNOR/`, `FASE-R4B-THERMAL-TEST/`, `FASE-R4C-JITTER-OBSERVABILITY/`, `FASE-D-COUNTERS-AUDIT/`, `R-14-SUPERPOSITION-DISSECTION/`, `M1-cap-35-30/`, `fase-a-discriminacion-*/`, `fase-b-cap-probe-*/`, `ep05-*/`, `ep06-*/`, `WORKLOAD-SINTETICO/`, `EXPLORATORIO-GravityMark/`, `results/` (1.102) + `~/rx550-power-sweep-20260918-132309/` y `~/rx550-power-sweep-20260918-140527/` (388) | `03-EXPERIMENTOS/` | 2026-09-23 | 1.490/1.490 hashes idénticos (conjunto, insensible a orden) | Evidencia experimental y datos de power-sweep |
| 6 | `projects/` (47) + `rx550-torneo/` (28) | `04-IMPLEMENTACION/` | 2026-09-23 | 75/75 idénticos (pre/post grupo); total 89 con los 14 diseños previos | Implementaciones y herramienta del torneo |
| 7 | `experiments/FASE-R0-EXTERNAL-KNOWLEDGE/` (8) + `~/Escritorio/RX550_Benchmarks/` (6) | `05-FUENTES-EXTERNAS/` | 2026-09-23 | 14/14 idénticos (pre/post grupo) | Fuentes externas de referencia |
| 8 | Verificación global post-movimiento | toda la raíz | 2026-09-23 | **1.645/1.645 manifest verificados ruta-por-ruta (0 faltantes, 0 modificados, 0 sin mapear) + 6/6 Benchmarks** | Integridad y cierre de la fase |

## Verificación de integridad

- [x] Post-movimiento: comparar hashes destino vs `REORGANIZACION-MANIFEST.sha256` → **1.645/1.645 verificados ruta por ruta** (origen→destino mapeado) + suplementario grupo 05 (14/14). Total movido autorizado: **1.651 archivos**.
- [x] Conflicto de nombres: ninguno detectado (preservación de nombres y estructura interna por carpeta).
- [x] Operaciones destructivas: CERO (no se borra, no se sobrescribe, no se modifica contenido).

> Nota metodológica: las dos verificaciones de grupo que reportaron "FALLO" durante la ejecución (grupo 03 y la global) fueron artefactos del comando verificador, no del movimiento — (a) el listado se generaba ordenado por ruta origen/destino (difieren en prefijo) y el `diff` era sensible a orden; (b) el `find -print` evaluaba las exclusiones `! -path` después de imprimir, y los 6 archivos de `RX550_Benchmarks` no pertenecen al manifest. La verificación corregida (comparación de multiconjuntos de hashes y mapeo ruta→ruta) confirma integridad total: **0 archivos perdidos, 0 modificados, 0 sin mapear**.