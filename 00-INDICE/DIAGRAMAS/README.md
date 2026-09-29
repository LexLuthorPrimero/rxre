# DIAGRAMAS — índice, convención y provenance

**STATUS:** DRAFT/CONFLICT
**LAST AUDITED:** 2026-09-25
**Ámbito:** vistas derivadas de la documentación canónica. Esta carpeta no autoriza acciones.

## Propósito

Esta carpeta proporciona diagramas técnicos legibles directamente desde Markdown para explicar:

- el estado del proyecto;
- el ciclo de investigación y autorización;
- dependencias de fases;
- hipótesis y experimentos asociados;
- telemetría, validación y veredictos;
- distinción entre documentación, diseño, autorización, ejecución y análisis;
- conflictos y unknowns que todavía impiden una vista `LIVE`.

Los diagramas no sustituyen la explicación textual ni la evidencia.

## Fuente de verdad

La autoridad documental es, en este orden:

1. `00-INDICE/MASTER-RESEARCH-STATUS.md` y sus addendas vigentes;
2. resultados canónicos de cada experimento;
3. `00-INDICE/MASTER-PLAN.md`, `IMPLEMENTATION-ROADMAP.md` y documentos de seguridad para estructura y límites;
4. auditorías y documentos de readiness para clasificaciones;
5. documentos de staging, hipótesis y sus fuentes;
6. snapshots históricos únicamente para trazabilidad.

Un diagrama es una **vista derivada**. Si el diagrama contradice al texto canónico, el texto canónico prevalece y el diagrama queda `CONFLICT` hasta corregirse.

## Inventario

| ID | Documento | Tipo | Estado actual |
|---|---|---|---|
| V-01 | `00-MAESTRO-PROYECTO.md` | Ciclo maestro y mapa general de capas | `DRAFT/CONFLICT` (actualizado) |
| V-02 | `01-ROADMAP-VISUAL.md` | Roadmap y dependencias por fases | `DRAFT/CONFLICT` |
| V-03 | `02-HIPOTESIS-H1-H12.md` | Claims C1 e hipótesis H1–H12 | `DRAFT/CONFLICT` |
| V-04 | `03-ARBOL-DECISION-EXPERIMENTAL.md` | Gates, autorización y pipeline C1 | `DRAFT/CONFLICT` |
| V-05 | `04-DAG-CAUSAL-RX550.md` | DAG cross-layer e historial de fallos | `DRAFT/CONFLICT`; causalidad no demostrada |
| V-06 | `05-TELEMETRIA-EVIDENCIA.md` | Pipeline de telemetría, evidencia y análisis | `DRAFT/CONFLICT` |
| V-07 | `06-H12-WSI-FRAMETIME.md` | Flujo H12/WSI/frametime | `DRAFT/CONFLICT`; capability parcial |
| V-08 | `07-RAMAS-INVESTIGACION.md` | Automatizador v1.1.0 y namespaces | `DRAFT/CONFLICT`; runtime no ejecutado |
| V-09 | `08-AUTORIZACION-SEGURIDAD.md` | Agentes externos, seguridad y autorización | `DRAFT/CONFLICT` |
| V-10 | `09-ESTADOS-CIENTIFICOS.md` | State machine científico provisional | `DRAFT/CONFLICT` (presente) |
| V-11 | `10-NAVEGACION-DOCUMENTAL.md` | Navegación de referencia/historical | `DRAFT/CONFLICT` (presente) |
| V-12 | `11-C1-STATE-MACHINE.md` | State machine C1 solicitada vs implementada | `DRAFT/CONFLICT` |
| V-13 | `12-MATRIZ-TRAZABILIDAD.md` | Matriz requisito→evidencia→test→runtime | `DRAFT/CONFLICT` |
| V-14 | `13-REGLA-FUNDAMENTAL.md` | Regla de publicación visual y no-causalidad | `DRAFT` |
| V-15 | `15-C1-ISOLATION-DESIGN.md` | Flujo de diseño de aislamiento previo a C1 | `DOCUMENTARY DESIGN`; `PREPARED_FOR_REVIEW`; no ejecución |

Las vistas V-01–V-14 están presentes y permanecen `DRAFT/CONFLICT` mientras las fuentes canónicas conserven `UNKNOWN`, `NOT_PROVEN`, `NOT_AVAILABLE`, `NOT_TESTED` o `CONFLICT`. V-15 es `DOCUMENTARY DESIGN` y no es evidencia de ejecución. La creación de un archivo no implica que su estado sea `LIVE`.

Los diagramas locales de R-4B, R-4A, FASE D, FASE G, telemetría y counters permanecen vinculados a
sus documentos fuente; no se duplican como un veredicto independiente.

## Convención Mermaid

Se usará Mermaid embebido en Markdown, sin imágenes rasterizadas:

- `flowchart TD` o `flowchart LR` para procesos, dependencias, gates y DAGs.
- `stateDiagram-v2` para ciclo de vida de evidencia, hipótesis y experimentos.
- `classDiagram` únicamente para relaciones entre capas o proveedores de telemetría.
- `subgraph` para separar fases, tracks o dominios.
- IDs ASCII estables y labels entre comillas.
- Sintaxis conservadora compatible con Markdown/GitHub/GitLab.
- Dividir cualquier diagrama que supere aproximadamente 40–50 nodos o que deje de ser legible.

### Formas

| Forma | Uso |
|---|---|
| Rectángulo | documento o proceso |
| Rombo | decisión |
| Hexágono | hipótesis o preparación |
| Subroutine | experimento |
| Stadium | gate o autorización |
| Cilindro | dataset o telemetría |
| Doble círculo | estado terminal explícito |

### Prefijos textuales

El prefijo siempre aparece dentro del label; el color nunca es la única información:

- `[DOC]` documentación o fuente;
- `[DESIGN]` diseño no ejecutado;
- `[AUTH]` autorización requerida o concedida;
- `[EXEC]` ejecución;
- `[ANALYSIS]` análisis;
- `[VERDICT]` veredicto;
- `[SNAPSHOT]` documento histórico;
- `[CONFLICT]` fuentes incompatibles;
- `[UNKNOWN]` evidencia insuficiente;
- `[HISTORICAL]` capacidad o resultado histórico;
- `[REQUIRES CAPABILITY AUDIT]` soporte/lectura local no confirmado;
- `[REQUIRES AUTHORIZATION]` acción prohibida hasta permiso nuevo.
- `[SOURCE]` fuente o artefacto de origen;
- `[READ-ONLY]` observación sin escritura;
- `[EVIDENCE]` artefacto o dataset;
- `[OBSERVATION]` observación medida;
- `[DECISION]` decisión o clasificación;
- `[IMPLEMENTATION]` diseño o implementación;
- `[STATIC]` implementación/evidencia estática registrada, sin runtime;
- `[CAPABILITY]` mecanismo que un componente puede usar;
- `[OBSERVED]` actividad observada en una ventana/artefacto concreto;
- `[PROVEN CAUSALITY]` vínculo causal sustentado por un gate y evidencia;
- `[FAIL-CLOSED]` bloquea y preserva estado ante fallo;
- `[RUNTIME VALIDATION]` validación de ejecución, no diseño.

### Flechas

| Flecha | Significado |
|---|---|
| `──>` | flujo o dependencia explícita |
| `-.->` | relación hipotética, documental o no causal |
| `==>` | gate, bloqueo o autorización |
| `---` | separación de tracks o clasificación |

Una relación causal no se dibuja como flecha sólida sin que exista un gate y evidencia que lo sostengan.

### Colores

Se usarán `classDef` y `class` de forma conservadora:

```text
LIVE                 azul
DRAFT                amarillo
SNAPSHOT             gris
CONFLICT             rojo
UNKNOWN              morado
VERIFIED             verde
INCONCLUSIVE         naranja
AUTHORIZATION        rojo oscuro
```

Cada diagrama debe conservar además una explicación textual de su estado.

## Provenance obligatorio

Cada diagrama debe incluir antes del bloque Mermaid:

```markdown
**DIAGRAM_ID:** V-XX
**STATUS:** LIVE | DRAFT | SNAPSHOT | CONFLICT | UNKNOWN | REQUIRES CAPABILITY AUDIT | REQUIRES AUTHORIZATION
**SOURCE_OF_TRUTH:**
- ruta/documento canónico
- resultado o auditoría complementaria
**LAST AUDITED:** AAAA-MM-DD
**CONFLICTS:** lista explícita o `none identified`
**NOTE:** este diagrama es una vista derivada y no autoriza acciones.
```

Si el diagrama contiene una afirmación que no puede rastrearse hasta una fuente, debe marcarse `UNKNOWN` o `REQUIRES CAPABILITY AUDIT`.

## Estados de publicación

| Estado | Significado |
|---|---|
| `LIVE` | Vista derivada reauditada y compatible con las fuentes canónicas; no autoriza acciones por sí sola |
| `DRAFT` | Vista provisional en revisión; no representa un resultado |
| `SNAPSHOT` | Vista histórica preservada; no describe el estado actual |
| `CONFLICT` | Hay fuentes o convenciones incompatibles; prevalece el texto canónico |
| `UNKNOWN` | La evidencia o capacidad necesaria no está confirmada |
| `REQUIRES CAPABILITY AUDIT` | Falta enumeración/confirmación de una capacidad local |
| `REQUIRES AUTHORIZATION` | La acción queda bloqueada hasta una autorización concreta y separada |

## Reglas de publicación

1. Un diagrama `LIVE` no puede depender de una contradicción abierta.
2. Un diagrama no convierte `DESIGNED` en `EXECUTED`.
3. Un diagrama no concede autorización.
4. Un diagrama no convierte `INCONCLUSIVE` en `PASS` o `SUPPORTED`.
5. Un diagrama no convierte una capability histórica en soporte actual.
6. No se duplica el mismo diagrama en varios archivos. Se enlaza al documento canónico o se mantiene una sola vista.
7. Si un documento histórico contiene un diagrama, se conserva como `SNAPSHOT` y no se mezcla con una vista `LIVE`.
8. Las afirmaciones provisionales se escriben explícitamente como `DRAFT`, `CONFLICT`, `UNKNOWN` o `REQUIRES CAPABILITY AUDIT`.
9. Una modificación de un diagrama requiere reauditar sus fuentes.

## Conflictos actuales que impiden publicar todo como LIVE

- La capacidad runtime de H12/WSI, present timing, fdinfo, queues y barriers no está
  confirmada localmente.
- La capacidad runtime de PM/ASPM, PMU, SQTT/RGP y counters GFX8 sigue `UNKNOWN`.
- `W_SMU`, `mem_busy_percent` y MCLK reportada requieren conservar su semántica exacta;
  no se deben promover a vatímetro, bandwidth o DRAM data rate.
- Las fuentes ya contienen Addenda D6, umbrales 50 °C, y una roadmap F/G/K sin ciclo
  normativo; estas vistas aún no han sido reauditadas contra toda la documentación heredada.
- La taxonomía de estados y el mapa global permanecen `DRAFT/CONFLICT` hasta una
  reauditoría completa.
- El sidecar vigente de C1 registra 37/37 y hashes actuales; R5 conserva 24/24 y
  hashes históricos: `PROVENANCE_CONFLICT`.
- H12-2 (r1–r3), H12-1 r4/H12-3 y H12-4 static tienen alcopes distintos; no se
  fusionan como una sola evidencia runtime.
- El inventario canónico no declara un candidato M2 actual elegible; las etiquetas
  históricas de utilidad no cambian ese estado.
- `README.md` referencia `REORGANIZATION-MANIFEST.sha256`, mientras el archivo
  existente es `REORGANIZACION-MANIFEST.sha256`: `CONFLICT` de ruta.
- V-15 es `DOCUMENTARY DESIGN`; no es evidencia de ejecución, ownership o autorización.

## Nota de no autorización

La existencia de este README, de un diagrama o de un protocolo no autoriza:

- benchmarks;
- scripts;
- sysfs;
- DPM/PM/ASPM;
- Mesa/kernel/firmware;
- counters;
- servicios;
- resets;
- cambios de configuración.

La autorización vive exclusivamente en el documento y en la decisión explícita de la persona responsable.

## Fuentes técnicas de Mermaid

- [Mermaid Flowchart](https://mermaid.js.org/syntax/flowchart.html)
- [Mermaid State Diagrams](https://mermaid.js.org/syntax/stateDiagram.html)
- [Mermaid Class Diagrams](https://mermaid.js.org/syntax/classDiagram.html)
