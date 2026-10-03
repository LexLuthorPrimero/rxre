# RX550 — Índice canónico de la investigación

Este archivo es el **índice canónico de la estructura actual** de
`RX550-INVESTIGACION/`. Las rutas de navegación están expresadas desde la raíz del
repositorio. Las referencias al backup y a la raíz antigua se conservan en la sección
histórica, pero no son localizadores operativos actuales.

## Cierre de consolidación 2026-09-25

- `../PATCH-REGISTRY-FINAL.md` — registro único de correcciones y procedimientos.
- `../PROBLEM-STATUS-FINAL.md` — estados finales por problema.
- `../INSTALL.md`, `../ROLLBACK.md`, `../TESTING.md` — preparación, rollback y pruebas.
- `../ESTADO.md` — gates de publicación, informe de release y bloqueos. Consolida
  los documentos de estado que se movieron a
  `../archive/documentacion-compactada-20261003/`.
- `../01-AUDITORIA/FINAL-VALIDATION/` — captura read-only de la instalación actual.

La consolidación no declara resueltos la estabilidad, DPM/PM, KWin/Wayland,
VFIO, C1, RA24 ni la disponibilidad de extensiones Vulkan. El estado editorial
`READY_FOR_GITHUB=NO` prevalece sobre cualquier resumen histórico.

## Cómo empezar

1. **`00-INDICE/MASTER-RESEARCH-STATUS.md`** — estado vigente, Addenda D6, ASIC/counters y Gate P0.
2. **`../ESTADO.md`** — estado consolidado del compresor, la publicación y el host.
   Incorpora el resumen histórico del cierre que estaba en
   `archive/documentacion-compactada-20261003/FINAL-RESEARCH-STATUS.md`.
3. **`02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt`** — especificación técnica de
   construcción de `rx550-torneo` (45 secciones).
4. **`00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md`** — mapa de navegación `DRAFT/CONFLICT` por capas.
5. **`00-INDICE/PROJECT-DOCUMENTATION-STATUS.md`** — estado por elemento del ecosistema.
6. **`00-INDICE/DIAGRAMAS/README.md`** — convención de vistas Mermaid `DRAFT/CONFLICT`.
7. **`00-INDICE/HYPOTHESIS-REGISTER.md`** — registro textual H1–H12, sin veredictos.

## Estado

**`../ESTADO.md`** es el documento único de estado del proyecto. Consolida seis
documentos que se declaraban "estado final" y competían entre sí
(`PROYECTO_STATUS.md`, `CIERRE_PROYECTO.md`, `RELEASE-CANDIDATE.md`,
`FINAL-RELEASE-REPORT.md`, `RELEASE-EXCLUSIONS.md`,
`00-INDICE/FINAL-RESEARCH-STATUS.md`), con las cifras medidas, sus limitaciones y
la fuente de cada una. Los originales están en
`archive/documentacion-compactada-20261003/`, con su manifiesto y sus hashes.

`PATCH-REGISTRY-FINAL.md` y `PROBLEM-STATUS-FINAL.md` siguen en la raíz: los
citan 23 y 27 documentos respectivamente, y son canónicos, no duplicados.

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
  `runs/20260919-235939/` y detalle en `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md`.

## Capas de navegación

- `01-AUDITORIA/` — auditorías documentales, readiness y auditorías de hardware.
- `02-ARQUITECTURA/` — arquitectura, conocimiento y mapa Polaris12.
- `03-EXPERIMENTOS/` — fases, datos, telemetría y resultados.
- `04-IMPLEMENTACION/` — diseños, `rx550-torneo/`, proyectos propios y roadmap.
- `05-FUENTES-EXTERNAS/` — fuentes, catálogos, benchmarks y manifiestos.
- `06-INGENIERIA-INVERSA/` — reverse engineering. **`findings/` es la fuente primaria
  del conocimiento** (499 `.md` a 2026-10-03); el resto son volcados de protocolo,
  mapas de registros, análisis de amdgpu y firmware.
- `07-DRIVER/` — driver especializado: `kernel/`, `driver/`, `userspace/`,
  `firmware/`, `tests/`, `build/`, `outgoing-reviews/`.
- `08-ARQUITECTURA/` — capa de trabajo activa: `decisions/`, `artifacts/`,
  `artifacts-rx550/`, `designs/`, `tools/`, `validations/`, `reviews/`,
  `logs-rx550/`. **`cache/` ocupa 9,6 GB y no es documentación.**
  Contiene `AGENTS.RECTOR-5d33ccab.bak`, copia del `AGENTS.md` canónico commiteado.
- `docs/` — addenda de prompt y auditorías. Contiene un `CONTRADICTIONS.md` **propio y
  escrito a mano**, distinto del `CONTRADICTIONS.md` de la raíz, que es una vista
  generada; no son intercambiables.
- `tools/` — herramientas de análisis del corpus. `tools/artifacts.py` genera las cinco
  vistas de estado, `tools/relations.py` extrae aristas entre hallazgos y
  `tools/frontier.py` clasifica huecos por vía de cierre.
- `revkit/` — kit de captura y verificación en Python, con `capturas/`.
- `archive/` — `prompts/`: versiones V6 a V11 del prompt rector, nombradas por hash.

## Defectos conocidos de este índice

Medidos el 2026-10-03. No están resueltos; están declarados para que nadie los
tome por rutas válidas.

- Las cinco vistas de la raíz (`CURRENT-STATE.md`, `CONTRADICTIONS.md`,
  `OPEN-FRONTIERS.md`, `EVIDENCE-MATRIX.md`, `KNOWLEDGE-GRAPH.md`) son **generadas** por
  `tools/artifacts.py` y declaran `NO EDITAR A MANO`. Sus cifras van minutos por detrás
  del registro de hallazgos, porque el registro cambia entre ejecuciones: una
  discrepancia entre esas cifras y el disco es **desfase esperado**, no error.
- El identificador numérico de un hallazgo **no lo identifica**: hay números
  compartidos por varios ficheros, y las cabeceras que citan `CORRECTS=041` en lugar
  del nombre completo producen aristas ambiguas en `KNOWLEDGE-GRAPH.md`, marcadas con
  `!`. Para citar, usar el nombre del fichero.
- `00-INDICE/README.md` y `R2-GLOBAL-DOCUMENTATION-MAP.md` se auditan el 2026-10-03:
  las 98 rutas backtickadas que citan resuelven. La última que no resolvía
  (`WORKLOAD-SINTETICO/README.md`, sin directorio padre) se corrigió ese día. Un
  `README.md` con basename ambiguo no se reescribe automáticamente: se corrige a mano,
  porque 37 ficheros del corpus se llaman `README.md`.

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
