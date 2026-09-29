# IMPLEMENTATION-ROADMAP.md — Hoja de ruta de implementación

**Ubicación canónica:** `04-IMPLEMENTACION/`
**Estado:** hoja de ruta **documental y planificada**; no es una autorización de ejecución.

## Principios

1. Primero caracterizar; después diseñar; después ejecutar un A/B aislado.
2. FPS/frametime es la métrica primaria; potencia, clocks, VRAM y utilización son
   variables explicativas.
3. Una hipótesis no se promueve a implementación sin evidencia y sin reversibilidad.
4. Toda escritura de sistema pasa por autorización explícita, snapshot, readback,
   restore y verificación posterior.
5. No se ejecutan benchmarks, scripts, contadores ni código descargado como parte de este
   documento.

## Orden recomendado

La columna **dependencia de diseño** no implica que la fase siguiente ya esté ejecutada.
La columna **dependencia de implementación** solo se activa después de una gate explícita.
Así F/G/K no forman un ciclo: F y G pueden diseñar sus contratos; K puede
construir el framework sin depender de que F o G hayan producido un resultado.

| Orden | Línea | Estado actual | Dependencia de diseño | Dependencia de implementación | Gate de salida |
|---|---|---|---|---|---|
| 0 | Preservación y observabilidad read-only | **EN TABLERO / NO ESCRITURA** | Manifest, telemetría y estados existentes | Ninguna | Evidencia localizable, hashes y estados inequívocos |
| 1 | FASE G: memoria/VRAM/GTT | **DISEÑADA, NO EJECUTADA** | FASE-D read-only y semántica R-4A | Ninguna para el diseño; runner solo después de K | Modelo request→cache→VRAM/GTT→PCI separado de hipótesis; bandwidth real `UNKNOWN` |
| 2 | FASE F: geometría | **DISEÑADA, NO EJECUTADA** | Workload gráfico y contrato de telemetría de G | K solo para implementación/medición | Candidatos GEO con métrica y confounders; sin causalidad declarada |
| 3 | FASE K: Performance Lab | **DISEÑADA, NO IMPLEMENTADA** | Contratos de F/G y estructura de runs | Autorización separada para código/framework | Runner, regresión y A/B reproducibles; no se ejecuta aquí |
| 4 | FASE L: RX550-Tuner | **DISEÑADA, NO IMPLEMENTADA** | K + ownership | K validado y autorización de writes | Perfil reversible y estado verificado |
| 5 | FASE M: contadores GFX8 | **CATÁLOGO DOCUMENTADO; ESCRITURA NO AUTORIZADA** | R-0/R-1 y capability audit | Autorización separada; nunca heredada de K | Mapa semántico de eventos y protocolo de counters separado |
| 6 | FASE E: baseline de juego real | **DISEÑADA, BLOQUEADA** | Juego reproducible y licencia | Autorización de instalación/ejecución | No iniciar sin fuente reproducible autorizada |
| 7 | FASE N–Q: investigación de ecosistema/Mesa | **PLANIFICADA** | K/I/M como contexto | Dependencia de cada línea y autorización propia | Solo discovery/A-B aislados; no cambios permanentes |

### Regla de no-ciclo F/G/K

- **F/G** pueden cerrar su diseño y telemetría sin implementar K.
- **K** puede definir el framework y los contratos de medición sin esperar un resultado de F/G.
- **F/G** solo consumen K como dependencia de implementación, después de una gate separada.
- La rama de optimización (L/M/N–Q) queda fuera del camino principal hasta que exista evidencia suficiente.


## Criterios de promoción

- **IDEA/HIPÓTESIS:** no tiene evidencia suficiente para implementar.
- **DISEÑADO:** existe protocolo reproducible, pero no se ha ejecutado.
- **EJECUTADO:** existe al menos una corrida documentada, no necesariamente válida.
- **VALIDADO:** la evidencia cumple los criterios definidos y es reproducible.
- **INCONCLUSO:** la muestra o las precondiciones no permiten decidir.
- **HISTÓRICO:** se conserva para trazabilidad, pero no es una especificación actual.

Una fila nunca se eleva a `VALIDADO`/`SUPPORTED` por una referencia, un nombre de archivo
o una inferencia. R-4B permanece `INCONCLUSO` bajo D6.

## Dependencias y seguridad

- La frontera de escrituras y las paradas de emergencia están en
  `IMPLEMENTATION-SAFETY-RULES.md` (misma carpeta).
- El estado vivo del proyecto está en `00-INDICE/MASTER-RESEARCH-STATUS.md`.
- El mapa de documentos está en `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md`.
- Este roadmap no modifica el worktree operativo ni autoriza scripts, servicios o
  benchmarks.

## C1 Isolation Design checkpoint (2026-09-25)

- `C1-ISOLATION-DESIGN-v1.0.md` = `PREPARED_FOR_REVIEW`; `DOCUMENTARY_ONLY`.
- Define `OWNERSHIP=FULL`, prechecks, guard `T_GUARD=120s`/muestras `5s`, GO/NO-GO/ABORT y restore plan.
- `RESTORE_VALIDATED=NO`; `C1=DEFERRED`; no se autoriza `--run` ni materialize runtime v2.
- Flujo derivado: `00-INDICE/DIAGRAMAS/15-C1-ISOLATION-DESIGN.md`.
- `GAP_REVIEW=COMPLETE`; `IMPLEMENTATION_GAPS_CLOSED=0`; no se cerró ningún gap de implementación.
- Próxima acción formal: `REQUEST_SEPARATE_AUTHORIZATION_BEFORE_IMPLEMENTATION_OR_RUNTIME`; no ejecución.
