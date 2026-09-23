# RX550 — Investigación iterativa (directorio de trabajo)

Índice de documentación. Léelo en el siguiente orden.

## Cómo empezar
1. **`FINAL-RESEARCH-STATUS.md`** — resumen ejecutivo: qué sabemos / no sabemos / descartado / sin
   reproducir, y qué se recomienda implementar. (2-3 min.)
2. **`RX550_BUILD_SPECIFICATION.txt`** — la especificación técnica de construcción de `rx550-torneo`.
   Este es EL documento de ingeniería para implementar el programa (45 secciones).
3. **`README.md`** (este archivo) — mapa de documentación.

## Archivos de investigación (cerrados al 2026-09-19)
| Archivo | Contenido |
|---|---|
| `knowledge.md` | Conocimiento verificado/reproducible vigente (identidad, energía, Mesa, operacional). |
| `evidence.md` | Referencias a experimentos y datos (EP-05/EP-06 y base reproducible). |
| `hypotheses.md` | Confirmadas / descartadas / no reproducibles, separadas por clase. |
| `decisions.md` | Datos de decisión de toda la investigación (incl. qué se autorizó y cerró). |
| `open_questions.md` | Preguntas realmente abiertas (causa raíz del régimen histórico, MCLK, bottleneck). |
| `research_log.md` | Bitácora día a día 17→19/09. |
| `experiments_proposed.md` | Estado de experimentos: ejecutados, cerrados, BLOQUEADOS (Fase C/EP-09, EP-07, EP-03). |
| `rejected_ideas.md` | Ideas refutadas con el peso de cada refutación. |

## Datos experimentales crudos
- `experiments/fase-a-discriminacion-20260919-114241/` — Fase A (+ RESULTADOS-FASE-A.md).
- `experiments/fase-b-cap-probe-20260919-122038/` — Fase B + EP-08.
- `experiments/ep06-soak-cap-20260919-205645/` — EP-06.
- `experiments/ep05-mesa-custom-20260919-212249/` — EP-05.
- `experiments/M1-cap-35-30/` — **M1 (COMPLETADO 2026-09-20)**: cap sostenido 35 W vs 30 W → NO
  DISCRIMINATIVO. Datos en `runs/20260919-235939/`; detalle en `RESULTADOS-M1.md`.
- Históricos (17/09, NO reproducibles): `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/`.

## Estado del sistema
Sin writes sysfs pendientes; cap 35 W; DPM auto; kalm real intacto; display en Intel HD 4600.
GPU objetivo (RX 550, `1002:699f`) es secundaria y sin salida de video (decisión deliberada de seguridad).