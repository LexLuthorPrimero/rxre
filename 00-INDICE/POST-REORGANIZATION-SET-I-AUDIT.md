# POST-REORGANIZATION-SET-I-AUDIT.md

> **Fase:** auditoría SOLO LECTURA del conjunto preliminar **Set I** (nuevos hallazgos post-reparación A–G).
> **Fecha:** 2026-09-23 · **Modo:** inspección y verificación de correspondencia objeto/destino; **cero archivos modificados** (confirmado §8).
> **Objetivo:** catalogar, clasificar y proponer (sin aplicar) las correcciones para las referencias vivas hacia `04-IMPLEMENTACION/projects/` detectadas como *no planificadas* en la fase A–G.

---

## 1. Inventario completo

Contexto de movimiento (fuente: `REGISTRO-DE-MOVIMIENTOS.md:14`): `projects/` (47 archivos) + `rx550-torneo/` (28) → `04-IMPLEMENTACION/`, verificado 75/75 + 14 diseños previos = 89. **Todas** las referencias inventariadas apuntan a objetos que hoy residen en `04-IMPLEMENTACION/projects/` (14 directorios = 10 ideas R-3 + 4 proyectos R-2).

| # | Archivo | Línea | Referencia exacta (texto en el doc) |
|---|---|---|---|
| R1 | `00-INDICE/MASTER-PLAN.md` | 793 | `` `projects/BERRETA/BERRETA-DESIGN.md` `` (fila R-2.14) |
| R2 | `00-INDICE/MASTER-PLAN.md` | 794 | `` `projects/GHOST/GHOST-CACHE-DESIGN.md` `` (fila R-2.15) |
| R3 | `00-INDICE/MASTER-PLAN.md` | 795 | `` `projects/RX-COMPRESSION-ENGINE/RX-COMPRESSION-ENGINE-DESIGN.md` `` (fila R-2.16) |
| R4 | `00-INDICE/MASTER-PLAN.md` | 796 | `` `projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` `` (fila R-2.17) |
| R5 | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | 47 | `` ## 2. Proyectos propios (`projects/`) `` |
| R6 | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | 51 | `` `projects/BERRETA/BERRETA-DESIGN.md` `` |
| R7 | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | 52 | `` `projects/GHOST/GHOST-CACHE-DESIGN.md` `` |
| R8 | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | 53 | `` `projects/RX-COMPRESSION-ENGINE/…DESIGN.md` `` (elipsis del autor) |
| R9 | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | 54 | `` `projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` `` |
| R10 | `01-AUDITORIA/FASE-R3-NOVELTY-AUDIT/FASE-R3-FINAL-REPORT.md` | 119 | `` dirs `projects/I-*` `` |
| R11 | `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md` | 43 | `` `projects/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md` `` (§4, cita DN-07) |
| R12 | `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md` | 45 | `` `projects/CLOSED-LOOP-QUALITY-GOVERNOR/POLARIS12-FEASIBILITY.md` `` |
| R13 | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md` | 12 | `` `projects/JITTER-REPROJECTION/EXPERIMENT-DESIGN.md` `` (hipótesis H2a-c) |
| R14 | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md` | 13 | `` `projects/JITTER-REPROJECTION/PRIOR-ART.md` `` (surveys TAA) |
| R15 | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md` | 14 | `` `projects/BERRETA/BERRETA-DESIGN.md` `` (fuera de integración — referencia) |

**Exhaustividad:** barrido residual post-A–G confirmó que en estos 5 archivos **no existen** otras ocurrencias de `projects/` además de las listadas (únicas excepciones: `MASTER-PLAN.md:774` y `FASE-R3-FINAL-REPORT.md:7`, ya reparadas en Sets A/C — verificado, y `PRECHECK-REPORT.md:58`, clasificada «no tocar» en §4).

### 1.1 Matriz de correspondencia objeto → destino (criterio del encargo: *no basta que la ruta exista*)

Se verificó que el destino existente es **el objeto que el documento pretende señalar**, contrastando título/contenido:

| # | Destino actual (`04-IMPLEMENTACION/projects/…`) | Existe | Evidencia de correspondencia |
|---|---|---|---|
| R1/R6/R15 | `BERRETA/BERRETA-DESIGN.md` | ✅ | Título `# BERRETA — Documento de Diseño del Proyecto`; contenido: overlap `async (ACE/compute)` + hipótesis H-B1..B3 (coincide con descripción R-2.14) |
| R2/R7 | `GHOST/GHOST-CACHE-DESIGN.md` | ✅ | Título `# GHOST — Ghost Cache — …`; contenido: prefetch, localidad, GTT vs VRAM, *working set* (R-2.15) |
| R3/R8 | `RX-COMPRESSION-ENGINE/RX-COMPRESSION-ENGINE-DESIGN.md` | ✅ | Título `# RX COMPRESSION ENGINE — …`; contenido: compresión de memoria (texturas, buffers, VRAM/GTT/PCIe) (R-2.16) |
| R4/R9 | `ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` | ✅ | Título `# ORQUESTADOR FINAL — …`; contenido: runner/telemetría/rollback + SAFETY BOUNDARY (R-2.17) |
| R10 | 10 ideas en dirs temáticos (ver §1.2) | ✅ | Sin dirs literales `I-*`; los 10 dirs reales llevan título `# (I-0X) …` en su diseño |
| R11 | `CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md` | ✅ | Título `# IDEA I-08 — CLOSED-LOOP QUALITY GOVERNOR: EXPERIMENT DESIGN`; §4 contiene **textualmente** «Record temp; abort/cool if >90 °C (DN-07 thermal policy)» — coincide con la cita de TEST-TERMICO |
| R12 | `CLOSED-LOOP-QUALITY-GOVERNOR/POLARIS12-FEASIBILITY.md` | ✅ | Título `# IDEA I-08 — CLOSED-LOOP QUALITY GOVERNOR: POLARIS12 FEASIBILITY` |
| R13 | `JITTER-REPROJECTION/EXPERIMENT-DESIGN.md` | ✅ | Título `# I-03 — EXPERIMENT-DESIGN — TAA JITTER AS REPROJECTION SIGNAL` (marco de H2a-c) |
| R14 | `JITTER-REPROJECTION/PRIOR-ART.md` | ✅ | Título `# I-03 — PRIOR ART — TAA JITTER…`; surveys TAA (Yang/Liu/Salvi, Hanika) |

### 1.2 Nota sobre «`projects/I-*`» (R10)

**No existe ni existió un directorio literal `I-*`** en `projects/` (viejo ni nuevo). `I-01…I-10` es el nomenclador interno de la fase R-3; los directorios reales tienen nombres temáticos. Mapeo verificado por títulos:

| Idea | Dir real | Idea | Dir real |
|---|---|---|---|
| I-01 | `TBDR-IMR` | I-06 | `GHOST-PREDICTIVE-CACHE` |
| I-02 | `TEMPORAL-TILE-REUSE` | I-07 | `ASYNC-OPTICAL-FLOW` |
| I-03 | `JITTER-REPROJECTION` | I-08 | `CLOSED-LOOP-QUALITY-GOVERNOR` |
| I-04 | `ROP-COMPUTE-OFFLOAD` | I-09 | `L2-RESIDENT-RENDERING` |
| I-05 | `GFX8-FRAME-RECORDER` | I-10 | `ASYNC-AUX-RENDERER` |

Precedente de estilo: `MASTER-RESEARCH-STATUS.md:194` (reparada en Set A) ya lo documenta como etiqueta sobre nombres temáticos: `` I-01..I-10 en `04-IMPLEMENTACION/projects/TBDR-IMR|TEMPORAL-TILE-REUSE|…` ``.

---

## 2. Clasificación de cada referencia

| # | Tipo | Naturaleza | ¿Debe cambiarse? | Confianza | Riesgo |
|---|---|---|---|---|---|
| R1 | **VIVA** | Fila de estado de tarea (R-2.14) en el plan maestro activo; apunta al diseño vigente | Sí | ALTA | BAJO |
| R2 | **VIVA** | Idem (R-2.15) | Sí | ALTA | BAJO |
| R3 | **VIVA** | Idem (R-2.16) | Sí | ALTA | BAJO |
| R4 | **VIVA** | Idem (R-2.17) | Sí | ALTA | BAJO |
| R5 | **VIVA** | Encabezado de sección del índice de estado documental activo (documento ya editado en Set A: L9/24/26) | Sí | ALTA | BAJO |
| R6–R9 | **VIVA** | Filas del mismo índice activo (§2) | Sí | ALTA | BAJO |
| R10 | **AMBIGUA** | Reporte de fase cerrada (histórico) que cita evidencia viva mediante **etiqueta no literal** (`I-*`); sin dirs literales en ningún árbol | Decisión (Propuesta A/B, §5) | MEDIA | BAJO–MEDIO |
| R11 | **VIVA** | Procedimiento activo read-only de la fase R-4B; cita el diseño vigente que fundamenta la política térmica (DN-07) | Sí | ALTA | BAJO |
| R12 | **VIVA** | Mismo documento; cita estudio de viabilidad vigente | Sí | ALTA | BAJO |
| R13 | **VIVA** | Precheck activo de la fase R-4C; cita diseño y prior art del experimento I-03 | Sí | ALTA | BAJO |
| R14 | **VIVA** | Idem | Sí | ALTA | BAJO |
| R15 | **VIVA** | Referencia cruzada («fuera de integración») al diseño BERRETA vigente | Sí | ALTA | BAJO |

Resultado: **14 referencias VIVAS reparables** (todos los destinos existen y corresponden al objeto) + **1 AMBIGUA** (R10) pendiente de decisión.

---

## 3. Propuesta antes → después (por referencia)

Modo previsto (si se autoriza la reparación I): reemplazo textual exacto 1:1, solo el prefijo `projects/` → `04-IMPLEMENTACION/projects/`, sin tocar el resto de la línea.

| # | Referencia actual (antes) | Propuesta (después) |
|---|---|---|
| R1 | `` `projects/BERRETA/BERRETA-DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/BERRETA/BERRETA-DESIGN.md` `` |
| R2 | `` `projects/GHOST/GHOST-CACHE-DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/GHOST/GHOST-CACHE-DESIGN.md` `` |
| R3 | `` `projects/RX-COMPRESSION-ENGINE/RX-COMPRESSION-ENGINE-DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/RX-COMPRESSION-ENGINE/RX-COMPRESSION-ENGINE-DESIGN.md` `` |
| R4 | `` `projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` `` |
| R5 | `` ## 2. Proyectos propios (`projects/`) `` | `` ## 2. Proyectos propios (`04-IMPLEMENTACION/projects/`) `` |
| R6 | `` `projects/BERRETA/BERRETA-DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/BERRETA/BERRETA-DESIGN.md` `` |
| R7 | `` `projects/GHOST/GHOST-CACHE-DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/GHOST/GHOST-CACHE-DESIGN.md` `` |
| R8 | `` `projects/RX-COMPRESSION-ENGINE/…DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/RX-COMPRESSION-ENGINE/…DESIGN.md` `` *(conservando la elipsis del autor)* |
| R9 | `` `projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` `` |
| R10 | `` dirs `projects/I-*` `` | **Propuesta A:** `` dirs `04-IMPLEMENTACION/projects/` `` · **Propuesta B:** sin cambio (ver §5) |
| R11 | `` `projects/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md` `` |
| R12 | `` `projects/CLOSED-LOOP-QUALITY-GOVERNOR/POLARIS12-FEASIBILITY.md` `` | `` `04-IMPLEMENTACION/projects/CLOSED-LOOP-QUALITY-GOVERNOR/POLARIS12-FEASIBILITY.md` `` |
| R13 | `` `projects/JITTER-REPROJECTION/EXPERIMENT-DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/JITTER-REPROJECTION/EXPERIMENT-DESIGN.md` `` |
| R14 | `` `projects/JITTER-REPROJECTION/PRIOR-ART.md` `` | `` `04-IMPLEMENTACION/projects/JITTER-REPROJECTION/PRIOR-ART.md` `` |
| R15 | `` `projects/BERRETA/BERRETA-DESIGN.md` `` | `` `04-IMPLEMENTACION/projects/BERRETA/BERRETA-DESIGN.md` `` |

---

## 4. Casos que NO deben tocarse

| Referencia | Motivo |
|---|---|
| `PRECHECK-REPORT.md:58` (`` projects/... → NO toca ``) | Nota **ilustrativa/meta** dentro del árbol listado del experimento; declara explícitamente que ese subárbol queda fuera; no es una ruta de localización de contenido |
| `FASE-R2-FINAL-REPORT.md` L42, L46, L64–65, L88, L92–95, L162–165, L185, L187 | Registros **históricos** de creación/backup/mapas de la fase R-2 (ya clasificados así en la auditoría previa; fuera del encargo I) |
| `R2-HISTORICAL-EXPERIMENT-INVENTORY.md` L19, L20, L30, L54, L193–199 | Método/backup/raíz histórica del repo iterativo — históricas |
| `02-ARQUITECTURA/evidence.md:25` | Backup `mesa-e*` histórico |
| `MASTER-PLAN.md:781` | **U5** (UNKNOWN): párrafo descriptivo del mapa documental; pendiente de decisión |
| `MASTER-PLAN.md:82` | `~/Escritorio/berchmark/instalados/` — destino externo deliberado, **no reparable** |
| `MASTER-PLAN.md:791–792, 797` (R-2.11/12/18: `FASE-L…`, `FASE-M…`, `FASE-O…`) | Nombres de archivo **desnudos** (sin prefijo `projects/`): fuera del alcance del Set I |
| Prohibiciones del encargo | Set H (scripts), U1–U5, logs, CSV/TSV, sysfs, snapshots, manifests/backups, NotebookLM, Mesa, `PROYECTOS_LUCAS`, exports |

---

## 5. Casos ambiguos

1. **R10 — `FASE-R3-FINAL-REPORT.md:119` (`projects/I-*`).**
   - *Ambiguo por:* (a) `I-*` es etiqueta del nomenclador interno de la fase R-3, no una ruta literal (no existió en ningún árbol); (b) el documento es un reporte de fase **cerrada** (2026-09-22), aunque referencia evidencia **viva**.
   - *Propuesta A (recomendada para navegabilidad):* reemplazar por `04-IMPLEMENTACION/projects/` (la raíz que contiene las 10 ideas) → texto: «dirs `04-IMPLEMENTACION/projects/`». Consistente con `MASTER-RESEARCH-STATUS.md:194` (Set A) que ya expresa la etiqueta sobre dirs temáticos.
   - *Propuesta B:* no tocar (intangibilidad del reporte de fase; la afirmación sigue siendo cierta).
   - *Recomendación:* **A**, con confianza MEDIA; decisión final del usuario.
2. **R8 — `PROJECT-DOCUMENTATION-STATUS.md:53` (elipsis `…DESIGN.md`).** La propuesta conserva la elipsis (estilo del autor). Alternativa opcional: expandir a `RX-COMPRESSION-ENGINE-DESIGN.md`. Sin bloqueo — se aplica la propuesta §3 salvo indicación contraria.
3. **Naturaleza de `PROJECT-DOCUMENTATION-STATUS.md`.** Tratado como documento **vivo** (consistente con su edición en Set A L9/24/26). Si se reinterpretara como snapshot histórico, R5–R9 también caerían; se mantiene el criterio vigente.

---

## 6. Riesgos

1. **Reporte de fase cerrada (R10):** editar un artefacto histórico de la fase R-3. *Mitigación:* cambio limitado a un locator; Propuesta B elimina el riesgo si se prefiere no tocar; la verificación hash antes/después + `git diff` 1:1 (mismo método A–G) acotaría el cambio a 1 línea.
2. **Elipsis (R8):** un reemplazo general podría expandir el nombre o romper el estilo. *Mitigación:* reemplazo textual exacto del substring con la elipsis conservada.
3. **Confusión «`I-*`» como ruta:** un lector podría buscar dirs literales `I-*` y no encontrarlos. *Mitigación:* este informe documenta el mapeo I-01…I-10 → dirs temáticos (§1.2); Propuesta A elimina el patrón de la cita.
4. **«La ruta existe ≠ es el objeto»:** riesgo inherente de toda reparación. *Mitigación (ya ejecutada en esta auditoría):* correspondencia objeto→destino verificada por títulos/contenido y por la cita textual §4 de TEST-TERMICO (matriz §1.1).
5. **Ampliación de alcance:** tocar líneas fuera de §3. *Mitigación:* lista cerrada de 5 archivos/15 referencias (§7) + verificación `git diff` contra HEAD; ninguna sustitución global.
6. **Inconsistencia de criterio vivo/histórico:** si se aprueba R10-A pero se niegan otras del mismo archivo, o si cambia el criterio sobre `PROJECT-DOCUMENTATION-STATUS`. *Mitigación:* decisiones explicitadas en §5 y reflejadas en el acta de autorización.
7. **Sin riesgo de ejecución:** esta fase es read-only; ninguna recuperación, harness, script ni cambio de sistema fue ejecutado (confirmado §8).

---

## 7. Lista exacta de archivos para una eventual reparación I

| # | Archivo | Líneas a modificar | Reemplazos |
|---|---|---|---|
| 1 | `00-INDICE/MASTER-PLAN.md` | 793, 794, 795, 796 | 4 |
| 2 | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | 47, 51, 52, 53, 54 | 5 |
| 3 | `01-AUDITORIA/FASE-R3-NOVELTY-AUDIT/FASE-R3-FINAL-REPORT.md` | 119 (*solo si se aprueba Propuesta A*) | 1 |
| 4 | `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md` | 43, 45 | 2 |
| 5 | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md` | 12, 13, 14 | 3 |

**Total: 5 archivos · 15 referencias** (14 VIVAS de cambio seguro + R10 condicional). Método propuesto: reemplazo exacto 1:1 de `projects/` → `04-IMPLEMENTACION/projects/` (patrón por entrada, no global), verificación por archivo (hash antes/después, `git diff` 1:1, destino existe, ref vieja desaparece solo donde corresponde) — idéntico protocolo a los Sets A–G.

---

## 8. Confirmación: esta fase NO modificó archivos existentes

- **Nada fue modificado** durante la auditoría Set I: las 36 correcciones A–G permanecen tal cual fueron entregadas y aceptadas.
- **Prohibiciones respetadas:** Set H intacto (10/10 hashes); UNKNOWNs U1–U5 intactos; sin logs/CSV/TSV/sysfs/snapshots/manifests/backups/NotebookLM/Mesa/PROYECTOS_LUCAS/exports tocados; sin benchmarks, scripts, harnesses ni cambios de sistema.
- **Evidencia de estado:** `git status --porcelain` al inicio y cierre de esta fase arroja exactamente los mismos 40 registros que al cierre de A–G = 36 archivos modificados (` M `) + **4 untracked** (`POST-REORGANIZATION-REFERENCE-REPAIR-PLAN.md`, `POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md`, `POST-REORGANIZATION-REFERENCES-AUDIT.md`, `REGISTRO-DE-REPARACION-REFERENCIAS.md`).
- **Único archivo creado en esta fase:** `00-INDICE/POST-REORGANIZATION-SET-I-AUDIT.md` (el presente informe, 5º untracked tras su creación).

---

*Fin de la auditoría Set I (solo lectura). En espera de autorización para la eventual reparación I.*
