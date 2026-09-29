# RX550 — Índice canónico de la investigación

Este archivo es el **índice canónico de la estructura actual** de
`RX550-INVESTIGACION/`. Las rutas de navegación están expresadas desde la raíz del
repositorio. Las referencias al backup y a la raíz antigua se conservan en la sección
histórica, pero no son localizadores operativos actuales.

## Cierre de consolidación 2026-09-25

- `../PATCH-REGISTRY-FINAL.md` — registro único de correcciones y procedimientos.
- `../PROBLEM-STATUS-FINAL.md` — estados finales por problema.
- `../INSTALL.md`, `../ROLLBACK.md`, `../TESTING.md` — preparación, rollback y pruebas.
- `../RELEASE-CANDIDATE.md` y `../FINAL-RELEASE-REPORT.md` — gates y publicación.
- `../01-AUDITORIA/FINAL-VALIDATION/` — captura read-only de la instalación actual.

La consolidación no declara resueltos la estabilidad, DPM/PM, KWin/Wayland,
VFIO, C1, RA24 ni la disponibilidad de extensiones Vulkan. El estado editorial
`READY_FOR_GITHUB=NO` prevalece sobre cualquier resumen histórico.

## Cómo empezar

1. **`00-INDICE/MASTER-RESEARCH-STATUS.md`** — estado vigente, Addenda D6, ASIC/counters y Gate P0.
2. **`00-INDICE/FINAL-RESEARCH-STATUS.md`** — resumen ejecutivo histórico del cierre; no
   sustituye al maestro vigente.
3. **`02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt`** — especificación técnica de
   construcción de `rx550-torneo` (45 secciones).
4. **`00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md`** — mapa de navegación `DRAFT/CONFLICT` por capas.
5. **`00-INDICE/PROJECT-DOCUMENTATION-STATUS.md`** — estado por elemento del ecosistema.
6. **`00-INDICE/DIAGRAMAS/README.md`** — convención de vistas Mermaid `DRAFT/CONFLICT`.
7. **`00-INDICE/HYPOTHESIS-REGISTER.md`** — registro textual H1–H12, sin veredictos.

## Documentos de investigación y arquitectura

| Documento | Ruta canónica | Contenido |
|---|---|---|
| Conocimiento | `02-ARQUITECTURA/knowledge.md` | Identidad, energía, Mesa, ASIC/counters y resultado del Gate P0. |
| Gate de validez | `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | Auditoría READ-ONLY de ownership, agentes, CPU, térmica, IRQ, almacenamiento, PM y PCI/power. |
| Evidencia | `02-ARQUITECTURA/evidence.md` | Referencias a experimentos y datos. |
| Hipótesis | `02-ARQUITECTURA/hypotheses.md` | Confirmadas, descartadas y no reproducibles. |
| Decisiones | `00-INDICE/decisions.md` | Decisiones de investigación y autorizaciones. |
| Preguntas abiertas | `02-ARQUITECTURA/open_questions.md` | UNKNOWN y preguntas no resueltas. |
| Bitácora | `02-ARQUITECTURA/research_log.md` | Registro histórico de sesiones. |
| Ideas descartadas | `02-ARQUITECTURA/rejected_ideas.md` | Refutaciones y evidencia asociada. |
| Experimentos propuestos | `00-INDICE/experiments_proposed.md` | Estado de experimentos y traspasos. |

## Datos experimentales crudos

- `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/` — Fase A.
- `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/` — Fase B y EP-08.
- `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/` — EP-06.
- `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249/` — EP-05.
- `03-EXPERIMENTOS/M1-cap-35-30/` — M1, cap 35 W frente a 30 W; datos en
  `runs/20260919-235939/` y detalle en `RESULTADOS-M1.md`.

## Capas de navegación

- `01-AUDITORIA/` — auditorías documentales, readiness y auditorías de hardware.
- `02-ARQUITECTURA/` — arquitectura, conocimiento y mapa Polaris12.
- `03-EXPERIMENTOS/` — fases, datos, telemetría y resultados.
- `04-IMPLEMENTACION/` — diseños, `rx550-torneo/`, proyectos propios y roadmap.
- `05-FUENTES-EXTERNAS/` — fuentes, catálogos, benchmarks y manifiestos.

## Sección histórica (no sustituye las rutas canónicas)

- Backup de las sesiones 17–19/09:
  `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/`.
- La antigua raíz `~/Escritorio/RX550_Iterative_Research/` se conserva vacía como resto
  histórico de la reorganización del 2026-09-23.
- Las rutas `experiments/`, `projects/` o `rx550-torneo/` que aparezcan en documentos
  históricos sin el prefijo actual deben leerse como referencias al estado anterior,
  salvo que el documento indique explícitamente que son una navegación vigente.

## Estado del sistema

Estado documentado del gate P0 (2026-09-24): **B. `CONTAMINATED_REQUIRES_ISOLATION`**.
El cap vigente es 35 W y DPM automático; `kalm`, `kalm-gpu`, `system-autopilot` y otros
autores permanecen activos, y existen clientes de la RX550. Display en Intel HD 4600;
la GPU objetivo (RX 550, `1002:699f`) es secundaria y no tiene salida de vídeo en el
snapshot. No hay autorización de tuning o A/B hasta aislar el entorno.
