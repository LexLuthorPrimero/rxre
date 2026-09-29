# POST-REORGANIZATION-REFERENCE-REPAIR-PLAN

> **FASE 7 — Resolución de ambigüedades y plan de parche (solo análisis).**
> **Fecha:** 2026-09-23 · **Modo:** read-only. **Unico entregable nuevo:** este archivo.
> **Base:** `00-INDICE/POST-REORGANIZATION-REFERENCES-AUDIT.md` (FASE 1–6) + verificación de existencias y
> lectura de contexto de los documentos ambiguos (todo verificado por inspección directa en esta fase).
> **Estado:** esperando autorización explícita para ejecutar cualquier parche de los Sets A–H.

---

## 0. Resumen ejecutivo

- La auditoría FASE 1–6 confirmó **0 hipervínculos Markdown y 0 symlinks** → todas las correcciones futuras
  son **edición textual 1:1** de rutas en 46 archivos (≈110 ediciones); nunca sustitución global.
- En FASE 7 se resolvieron las 5 ambigüedades con evidencia primaria (contexto de documento + existencias
  verificadas), no por intuición:
  1. **README-FASE2/3** → las refs describen el **contenido del repo** (hoy `04-IMPLEMENTACION/rx550-torneo`),
     **NO** los launchers bash de `$HOME`.
  2. **R2-GLOBAL-DOCUMENTATION-MAP** → documento **mixto**, predominante **mapa vivo** (navegación).
  3. **R2-HISTORICAL-EXPERIMENT-INVENTORY** → mixto con partición clara: Familia 1 (backup) histórica,
     Familia 2 + M1 = contenido vivo del repo.
  4. **Antiguo `00-INDICE/README.md`** → sus refs describen la **estructura anterior** (contenido que sigue
     existiendo y fue movido) → convertibles a nueva estructura; el **rol** del documento queda en decisión.
  5. **Comentarios de rutas en scripts** → los 3 detectados son **ilustrativos** (linaje/autocontención),
     no operativos → **no se modifican**.
- **RX550_Benchmarks:** confirmadas **2 referencias vivas** (`MASTER-PLAN.md:109,111`) → `05-FUENTES-EXTERNAS/RX550_Benchmarks/`;
  las referencias históricas (7 en `REORGANIZATION-AUDIT` + `MASTER-PLAN:82`) **NO se modifican**.
- Quedan **5 decisiones UNKNOWN** que bloquean parcialmente 3 conjuntos (ver §2).
- Cambios prohibidos (C/D/F) explicitados en §5; nada se ejecuta, se instala ni toca sistema/GPU.

---

## 1. Ambigüedades resueltas (con evidencia)

### A) README-FASE2/3 — ¿contenido movido o launcher de HOME?

**Resolución: describen contenido que vive hoy dentro de `RX550-INVESTIGACION` → se actualizan.**

Evidencia (inspección directa, no intuición):

| Fuente | Hallazgo |
|---|---|
| `README-FASE2.md:82-85` | Runbook: `cd ~/Escritorio/RX550_Iterative_Research/rx550-torneo` + `sudo ./rx550-torneo state-write-test --confirm --json` |
| `README-FASE3.md:143-147` | Runbook: `cd ~/Escritorio/RX550_Iterative_Research/rx550-torneo` + `./rx550-torneo cap-write-test` |
| Launcher del repo | `04-IMPLEMENTACION/rx550-torneo/rx550-torneo` (bash → `python3 -m rx550_torneo.cli`) |
| `~/rx550-torneo` (14.229 B, hash `bcc41451…`) | **Bash legado** "modo torneo" (v1) — `CARD=/sys/class/drm/card1`, sin subcomandos CLI Python |
| `~/bin/rx550-torneo` (16.760 B, hash `d0c25383…`) | **Bash legado** "modo torneo" (v2) — idem |
| `REORGANIZATION-AUDIT.md:45-46,49,131` | "No son duplicados (son herramientas distintas)"; launcher Python (235 B, `4b05d8c6…`) = **herramienta operativa actual**, vive en el repo |

Los subcomandos `state-write-test`/`cap-write-test` **solo existen en el CLI Python del repo**, no en los bash
legado de `$HOME`. Por lo tanto el `cd …/rx550-torneo` de los runbooks apunta al **directorio de la herramienta
que hoy está en `04-IMPLEMENTACION/rx550-torneo`**, y debe cambiar a la ruta nueva.

- **Propuesta:** `cd ~/Escritorio/RX550-INVESTIGACION/04-IMPLEMENTACION/rx550-torneo`
- **Confianza:** ALTA · **Riesgo:** BAJO.
- Relacionado: `README-FASE1.md:3` (`../RX550_BUILD_SPECIFICATION.txt`) → `../../02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` (destino verificado con `realpath -m` + existencia).

### B) R2-GLOBAL-DOCUMENTATION-MAP.md — ¿mapa vivo, snapshot o mixto?

**Resolución: MIXTO, predominante MAPA VIVO (navegacional); contiene componentes históricos.**

Evidencia de su propio texto:
- `:10-15` — Propósito: "Índice completo y navegable de toda la documentación… **dónde empieza un investigador
  nuevo**. Complementa a `PROJECT-DOCUMENTATION-STATUS.md`". Ese propósito es navegación → vivo.
- Secciones: §1 raíz + archivos raíz, §2 capa `experiments/`, §3 `rx550-torneo`, §5 rutas de navegación →
  describen **ubicación actual de contenido existente** (todo movido, todo sigue existiendo) → vivas.
- §4 Backup Torneo, y la descripción "4 capas" (§6) → **históricos** (el layout viejo ya no existe).

**Consecuencia para el parche (§3, Set B):** actualizar §1, §2, §3, §5 y la §6 al nuevo layout
(6 carpetas + README raíz); **NO tocar §4** (backup externo) ni las rutas de backups citadas.

### C) R2-HISTORICAL-EXPERIMENT-INVENTORY.md — ¿rutas históricas o contenido actual?

**Resolución: MIXTO con partición por familia; el propio doc la declara en `:202-203`**
("las rutas de la Familia 2 son relativas al repo activo").

| Grupo | Líneas | Naturaleza | Acción |
|---|---|---|---|
| Familia 1 (E1…E5b, E0, §4, §5) — artefactos en **backup** | 19, 30, 54, 141-142, 179-183, 193-199 | **Histórica/externa** | **NO modificar** |
| Familia 2 (E-01/02/03/ES-01/F2) `experiments/WORKLOAD-SINTETICO/` | 38, 164-168, 200 | Contenido vivo del repo → `03-EXPERIMENTOS/WORKLOAD-SINTETICO/` | **Actualizar** |
| M1 autorizado 2026-09-20 `experiments/M1-cap-35-30/` | 112 | Contenido vivo del repo → `03-EXPERIMENTOS/M1-cap-35-30/` | **Actualizar** |
| Línea de método `:20` (dónde se buscó, repo viejo) | 20 | Registro de acción pasada | **Histórica** (anotación opcional) |

Confianza del split: ALTA (verificado por existencia: `03-EXPERIMENTOS/WORKLOAD-SINTETICO/…` y
`03-EXPERIMENTOS/M1-cap-35-30/…` existen; los artefactos E-series solo existen en `…_Backup_2026-09-19_0836/`).

### D) Antiguo `00-INDICE/README.md` — ¿estructura anterior o convertirse?

**Resolución: sus referencias documentan la estructura ANTERIOR (nombres de raíz + prefijo `experiments/`),
respecto de contenido que sigue existiendo → conversibles a la nueva estructura (regla "documentación viva").**

Evidencia de contenido (lectura completa): "Índice de documentación"; §Cómo empezar (FINAL-RESEARCH-STATUS,
RX550_BUILD_SPECIFICATION, README), tabla de "Archivos de investigación (cerrados 09-19)", "Datos
experimentales crudos" (`experiments/…`) y línea de backup (`:31`).

| Referencia | Antes (estructura previa) | Propuesta |
|---|---|---|
| `README-FASE2.md`-equivalente: L8 | `RX550_BUILD_SPECIFICATION.txt` | `02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` |
| Tabla archivos cerrados L15-22 | `knowledge/evidence/hypotheses/open_questions/research_log/rejected_ideas` | `02-ARQUITECTURA/` · `decisions/experiments_proposed` quedan en `00-INDICE/` |
| Datos crudos L25-30 | `experiments/fase-a|fase-b|ep06|ep05|M1` | `03-EXPERIMENTOS/<dir>` |
| L31 backup | `~/Escritorio/RX550_Modo_Torneo_Backup_…` | **NO tocar** (externa F) |

- **Decisión abierta (UNKNOWN, §2):** si el archivo **permanece como índice activo** de `00-INDICE` (recomendado:
  se actualiza) o si se **depreca** a favor del README raíz nuevo (no se toca). Las refs individuales son
  clasificables con alta confianza; el **rol** del documento no.

### E) Comentarios de rutas dentro de scripts

**Resolución: los 3 comentarios detectados son ILUSTRATIVOS (descriptivos), no operativos → NO se modifican.**

| Script | Línea | Contenido | Clase |
|---|---|---|---|
| `FASE-R4B-GOVERNOR/telemetry/telemetria.sh` | 3 | "Patrón heredado de `experiments/EXPLORATORIO-GravityMark/telemetria.sh` (validado)" | **Ilustrativa** (linaje/proveniencia) |
| `FASE-R4B-THERMAL-TEST/run_thermal_replicate.sh` | 6 | "Escribe SOLO en `experiments/FASE-R4B-THERMAL-TEST/runs/repREP/`" | **Ilustrativa** (describe la propia salida `runs/rep<n>`) |
| `FASE-R4C-JITTER-OBSERVABILITY/harness/run_all.sh` | 3 | "manteniendo todo dentro de `experiments/FASE-R4C-JITTER-OBSERVABILITY/`" | **Ilustrativa** (invariante de autocontención, sigue siendo verdadero) |

Ninguna se usa en la lógica de ejecución. Se dejan intactas (alineación cosmética solo si el usuario la pide
explícitamente, después de los parches).

### F) RX550_Benchmarks — confirmación de las 2 refs vivas y las históricas

**Vivas (se modificarán en Set A — mismo archivo `MASTER-PLAN.md`):**

| Ref | Original | Propuesta |
|---|---|---|
| `MASTER-PLAN.md:109` | `~/Escritorio/RX550_Benchmarks/BENCHMARK-INVENTORY.md` | `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md` |
| `MASTER-PLAN.md:111` | `RX550_Benchmarks/docs/` (…`SOURCES-AND-EXECUTION.md`, `DOWNLOAD-MANIFEST.sha256`, `README.md`) | `05-FUENTES-EXTERNAS/RX550_Benchmarks/docs/…` |

**Históricas (NO se modifican):** `REORGANIZATION-AUDIT.md` (7 menciones: 17, 44, 147, 148, 149, 150, 214 —
inventario/duplicados/movimiento previo) y `MASTER-PLAN.md:82` (recuento de instalación en
`~/Escritorio/berchmark/instalados/`, externa deliberada). `MASTER-PLAN.md:104` es ref a `berchmark/` (externa),
no a `RX550_Benchmarks` → NO se modifica. Destino `05-FUENTES-EXTERNAS/RX550_Benchmarks/` verificado (contiene
`BENCHMARK-INVENTORY.md`, `docs/`, `official-downloads/`, `cancelled-downloads/`, `README.md`).

---

## 2. Ambigüedades que continúan UNKNOWN (requieren revisión/decisión)

Criterio de seguridad (§9 del encargo): si una referencia no se clasifica con alta confianza como "ruta actual
que debe actualizarse", se marca **UNKNOWN — requiere revisión** y NO se modifica.

| # | UNKNOWN | Impacto | Bloquea |
|---|---|---|---|
| U1 | **Rol de `00-INDICE/README.md`**: índice activo → se actualiza (Set A), o deprecado → no se toca | Afecta 1 archivo del Set A | Set A (parcial) |
| U2 | **Alcance del Set B**: convertir R2-GLOBAL-MAP en mapa vivo completo (recomendado) vs declararlo snapshot histórico y crear mapa nuevo | 1 archivo | Set B |
| U3 | **Re-ejecución futura de harnesses** (FASE D Etapa 2/3, R-14, soak): si no se re-ejecutarán, los parches de scripts del Set H son solo "higiene de reproducibilidad" con prioridad baja | Set H (prioridad/alcance) | Set H |
| U4 | **Extensión del Set G**: `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md:195,197` refieren `experiments/EXPLORATORIO-GravityMark/runs/…` (contenido vivo) — no estaban en los sets originales | +1 archivo en Set G | Set G (opcional) |
| U5 | **`MASTER-PLAN.md:781`**: mención de `experiments/`/`projects/` dentro de la descripción del entregable R-2.2 (redacción conceptual) | Cosmético | Set A (opcional) |

---

## 3. Sets A–G — parches propuestos

> **Mapeo de prefijos (raíz vieja → raíz nueva `~/Escritorio/RX550-INVESTIGACION/`)** — verificado contra el árbol actual:

| Prefijo original | Destino nuevo |
|---|---|
| `experiments/<dir experimento>` (fase-a, fase-b, ep05, ep06, M1, WORKLOAD-SINTETICO, EXPLORATORIO-GravityMark, R-14, FASE-D, FASE-R4A/R4B/R4C, FASE-R4B-THERMAL-TEST) | `03-EXPERIMENTOS/<dir>` |
| `experiments/POLARIS12-MAP` | `02-ARQUITECTURA/POLARIS12-MAP` |
| `experiments/AUDIT-001` | `01-AUDITORIA/AUDIT-001` |
| `experiments/FASE-R1-DOCUMENTATION-RECONCILIATION` | `01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION` |
| `experiments/FASE-R2-PROJECT-DOCUMENTATION` | `01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION` *(excepto `R2-GLOBAL-DOCUMENTATION-MAP.md` → `00-INDICE/`)* |
| `experiments/FASE-R3-NOVELTY-AUDIT` | `01-AUDITORIA/FASE-R3-NOVELTY-AUDIT` |
| `experiments/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT` | `01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT` |
| `experiments/FASE-R0-EXTERNAL-KNOWLEDGE` | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE` |
| `experiments/EXPLORATORIO-GravityMark/…` | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/…` |
| `projects/` | `04-IMPLEMENTACION/projects` |
| `FASE-P-*.md` (diseños) | `04-IMPLEMENTACION/` |
| Archivos de raíz vieja (`knowledge/evidence/hypotheses/open_questions/research_log/rejected_ideas`, `RX550_BUILD_SPECIFICATION.txt`) | `02-ARQUITECTURA/` |
| `~/Escritorio/RX550_Iterative_Research` (absoluta) | `~/Escritorio/RX550-INVESTIGACION` |
| `~/Escritorio/RX550_Benchmarks/` | `~/Escritorio/RX550-INVESTIGACION/05-FUENTES-EXTERNAS/RX550_Benchmarks/` |

**Leyenda tabla:** V/H = documentación **Viva** (ubicación actual de contenido movido → se actualiza) / **Histórica** (no se toca).

### SET A — Maestros vivos en `00-INDICE/`

| Archivo | refs | Referencia original → propuesta | Motivo | V/H | Confianza | Riesgo |
|---|---|---|---|---|---|---|
| `MASTER-RESEARCH-STATUS.md` | ≈40 | `experiments/<X>` → prefijo nuevo (regla de tabla); ejemplos: L35/36/367/368 (`fase-b`, `POLARIS12-MAP`→`02-ARQUITECTURA`), L54/365 (`AUDIT-001`→`01-AUDITORIA`), L129/380 (R0→`05-FUENTES`), L149/381/438 (R1→`01-AUDITORIA`), L169/382 (R2→`01-AUDITORIA`), L211/384 (R3-1→`01-AUDITORIA`), L235/385 (R4A), L255/386 (R4C), L281/387 (R4B), L372 (M1), L373-375 (WORKLOAD), L376-377 (EXPLORATORIO), L378 (R-14), L379/424 (FASE-D), L383 (`projects`→`04-IMPLEMENTACION`) | Fuente viva del estado; localiza contenido actual | V | ALTA | BAJO |
| `MASTER-PLAN.md` | 10 | L59 `~/Escritorio/RX550_Iterative_Research/rx550-torneo/ + experiments/` → `04-IMPLEMENTACION/rx550-torneo/ + 03-EXPERIMENTOS/` · L87 → `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/` · L109/111 → `05-FUENTES-EXTERNAS/RX550_Benchmarks/…` · L290 → `02-ARQUITECTURA/POLARIS12-MAP/…` · L325 → `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/…` · L338/728 → `01-AUDITORIA/FASE-R1-…` · L774 → `01-AUDITORIA/FASE-R2-…` + `04-IMPLEMENTACION/projects` · L781 (opcional, U5) | Plan vivo navegacional | V | ALTA | BAJO |
| `README.md` (índice legado) | 14 | L8 → `02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` · L15-22 → `02-ARQUITECTURA/` (6 docs) y `00-INDICE/` (2) · L25-30 → `03-EXPERIMENTOS/<dir>` · L31 backup NO | Regla doc viva; contenido sigue existiendo movido | V | ALTA (refs) / **U1** (rol) | BAJO |
| `PROJECT-DOCUMENTATION-STATUS.md` | 3 | L9 → `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` · L24 → `03-EXPERIMENTOS/fase-a-…` · L26 → `02-ARQUITECTURA/POLARIS12-MAP/` | Ubica entregables actuales | V | ALTA | BAJO |
| `FINAL-RESEARCH-STATUS.md` | 1 | L12 `experiments/M1-cap-35-30/RESULTADOS-M1.md` → `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md` | Idem | V | ALTA | BAJO |
| `decisions.md` | 1 | L41 `experiments/WORKLOAD-SINTETICO/RESEARCH.md` → `03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md` | Idem | V | ALTA | BAJO |
| `experiments_proposed.md` | 1 | L15 `experiments/M1-cap-35-30/RESULTADOS-M1.md` → `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md` | Idem | V | ALTA | BAJO |

### SET B — `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` (mapa mixto — ver §1B, U2)

| refs | Referencia original → propuesta | Motivo | V/H | Confianza | Riesgo |
|---|---|---|---|---|---|
| §1 (L23) | `/home/lucas/Escritorio/RX550_Iterative_Research/` → `…/RX550-INVESTIGACION/` + filas de archivos raíz → `00-INDICE/` o `02-ARQUITECTURA/` | Mapa vivo → nueva raíz | V | ALTA | MEDIO (mapa largo; parche en bloque) |
| §2 | `experiments/<X>` → prefijos nuevos (regla tabla) | Idem | V | ALTA | MEDIO |
| §3 | `rx550-torneo` → `04-IMPLEMENTACION/rx550-torneo` | Idem | V | ALTA | MEDIO |
| §5 | Rutas de navegación → nueva estructura | Idem | V | ALTA | MEDIO |
| §6 | Descripción "4 capas" → nueva estructura 6 carpetas (o nota histórica) | Histórico externo → actualizar o anotar | H/M | MEDIA (**U2**) | MEDIO |
| §4 (backup) | Rutas `RX550_Modo_Torneo_Backup_…` | Externa deliberada | H | — | **NO tocar** |

### SET C — `01-AUDITORIA/` (auto-ubicación y cross-refs)

| Archivo | refs | Referencia original → propuesta | V/H | Confianza | Riesgo |
|---|---|---|---|---|---|
| `AUDIT-001/AUDIT-001.md` | 1 | L256 `experiments/POLARIS12-MAP/` → `02-ARQUITECTURA/POLARIS12-MAP/` | V | ALTA | BAJO |
| `FASE-R3-1-…/README.md` | 1 | L3 self → `01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/` | V | ALTA | BAJO |
| `FASE-R3-1-…/FUSION-03-…md` | 1 | L32 → `03-EXPERIMENTOS/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md` | V | ALTA | BAJO |
| `FASE-R3-NOVELTY-AUDIT/FASE-R3-FINAL-REPORT.md` | 2 | L7 self → `01-AUDITORIA/FASE-R3-NOVELTY-AUDIT/` + `projects/`→`04-IMPLEMENTACION/projects/` | V | ALTA | BAJO |
| `FASE-R2-…/FASE-R2-FINAL-REPORT.md` | 3 | L7 self → `01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION/` · L64/185 (entregables: mapa→`00-INDICE/`, dir→`01-AUDITORIA/`) · L46 backup **NO** | V | MEDIA-ALTA | BAJO |
| `FASE-R2-…/R2-HISTORICAL-EXPERIMENT-INVENTORY.md` | 6 | L38/164-168/200 `experiments/WORKLOAD-SINTETICO/…` → `03-EXPERIMENTOS/WORKLOAD-SINTETICO/…` · L112 → `03-EXPERIMENTOS/M1-cap-35-30/` · L19/30/54/193-199 (backup) **NO** · L20 (método) histórico, anotación opcional | Mixto (ver §1C) | ALTA | BAJO |
| `FASE-R1-…/FASE-R1-FINAL-REPORT.md` | 2 | L5/106 self → `01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/` | V | ALTA | BAJO |
| `FASE-R1-…/R1-1-GFX8-EVENT-RECONCILIATION.md` | 1 | L143 → `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-ID-REFERENCE.txt` · L144 backup **NO** | V/H | ALTA | BAJO |

### SET D — `02-ARQUITECTURA/`

| Archivo | refs | Referencia original → propuesta | V/H | Confianza | Riesgo |
|---|---|---|---|---|---|
| `research_log.md` | 2 | L36/L43 → `03-EXPERIMENTOS/M1-cap-35-30/runs/20260919-235939` / `…/RESULTADOS-M1.md` · L8 backup **NO** | V | ALTA | BAJO |
| `evidence.md` | 5 | L8-12 → `03-EXPERIMENTOS/fase-a-…/`, `fase-b-…/` (×2), `ep06-…/`, `ep05-…/` · L3/25 backup **NO** | V | ALTA | BAJO |

### SET E — `03-EXPERIMENTOS/` (auto-ubicación y cross-refs internas)

| Archivo | refs | Referencia original → propuesta | V/H | Confianza | Riesgo |
|---|---|---|---|---|---|
| `FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL.md` | 1 | L3 → `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/` | V | ALTA | BAJO |
| `FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL-v2.2.md` | 1 | L10 → `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/` | V | ALTA | BAJO |
| `FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md` | 7 | L33/35/37/41/42 → `03-EXPERIMENTOS/…` · L39 `AUDIT-001`→`01-AUDITORIA/AUDIT-001/METRICS-DEFINITIONS.md` · L62 `…/harness/build/governor_harness` (artefacto C intacto; solo doc) → `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/harness/build/governor_harness` | V | ALTA | BAJO |
| `FASE-R4C-…/PRECHECK-REPORT.md` | 3 | L11 → `01-AUDITORIA/FASE-R3-1-…/FUSION-01-…md` · L15 → `04-IMPLEMENTACION/FASE-P-FRAME-GENERATION-UPSCALING-DESIGN.md` (ubicación verificada) · L115 → `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/` | V | ALTA | BAJO |
| `FASE-R4C-…/EXP-F1-A-RESULTADOS.md` | 2 | L10 → `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/harness/` + `results/` · L152 self → `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/` | V | ALTA | BAJO |
| `R-14-SUPERPOSITION-DISSECTION/R-14-SUPERPOSITION-DISSECTION.md` | 1 | L153 self → `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/` | V | ALTA | BAJO |
| `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-PLAN.md` | 5 | L213 `WORK=/home/lucas/…/RX550_Iterative_Research` → `WORK=/home/lucas/…/RX550-INVESTIGACION` · L217 → `${WORK}/03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/etapa2/A1` · L229 → `WORK/03-EXPERIMENTOS/EXPLORATORIO-GravityMark/telemetria.sh` · L257 → `cd ${WORK}/03-EXPERIMENTOS/WORKLOAD-SINTETICO` · L285 → `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/etapa2/` | V (plan operativo futuro) | ALTA | MEDIO |
| `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-PRECHECK.md` | 2 | L228-229 `…/RX550_Iterative_Research/experiments/…` → `…/RX550-INVESTIGACION/03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/snapshot-*.txt` | V | ALTA | BAJO |
| `FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md` | 2 | L174 → `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/` · L188 → `01-AUDITORIA/FASE-R1-…/R1-1-…md` · L22 backup **NO** | V/H | ALTA | BAJO |
| `WORKLOAD-SINTETICO/RESEARCH.md` | 2 | L225 → `03-EXPERIMENTOS/WORKLOAD-SINTETICO/src/compute.comp` · L712 → `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/telemetria.sh` | V | ALTA | BAJO |
| `M1-cap-35-30/RESULTADOS-M1.md` *(detectado FASE 7)* | 1 | L6 self → `03-EXPERIMENTOS/M1-cap-35-30/runs/20260919-235939` | V | ALTA | BAJO |
| `WORKLOAD-SINTETICO/runs/exploratorio-01/RESULTADO-EXPLORATORIO-01.md` *(detectado FASE 7)* | 1 | L7 → `03-EXPERIMENTOS/WORKLOAD-SINTETICO/` | V | ALTA | BAJO |

### SET F — `04-IMPLEMENTACION/`

| Archivo | refs | Referencia original → propuesta | V/H | Confianza | Riesgo |
|---|---|---|---|---|---|
| `rx550-torneo/README-FASE1.md` | 1 | L3 `../RX550_BUILD_SPECIFICATION.txt` → `../../02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` (verificado) | V | ALTA | BAJO |
| `rx550-torneo/README-FASE2.md` | 1 | L83 `cd ~/Escritorio/RX550_Iterative_Research/rx550-torneo` → `cd ~/Escritorio/RX550-INVESTIGACION/04-IMPLEMENTACION/rx550-torneo` | V (runbook) | ALTA | BAJO |
| `rx550-torneo/README-FASE3.md` | 1 | L144 idem | V (runbook) | ALTA | BAJO |
| `SYNTHETIC-WORKLOAD-DESIGN.md` | 1 | L6 `experiments/WORKLOAD-SINTETICO/` → `03-EXPERIMENTOS/WORKLOAD-SINTETICO/` | V | ALTA | BAJO |
| `FASE-E-REAL-GAME-BASELINE-DESIGN.md` | 1 | L31 `experiments/R-14-SUPERPOSITION-DISSECTION/` → `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/` | V | ALTA | BAJO |
| `FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md` | 1 | L7 `experiments/POLARIS12-MAP/EXPERIMENT-CANDIDATES.md` → `02-ARQUITECTURA/POLARIS12-MAP/EXPERIMENT-CANDIDATES.md` | V | ALTA | BAJO |

### SET G — `05-FUENTES-EXTERNAS/`

| Archivo | refs | Referencia original → propuesta | V/H | Confianza | Riesgo |
|---|---|---|---|---|---|
| `FASE-R0-…/FASE-R0-EXTERNAL-KNOWLEDGE-FINAL-REPORT.md` | 1 | L7 self `experiments/FASE-R0-EXTERNAL-KNOWLEDGE/` → `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/` | V | ALTA | BAJO |
| `FASE-R0-…/R0-2-POWERPLAY-MCLK-SMU7.md` | 2 | L25/114 → `03-EXPERIMENTOS/WORKLOAD-SINTETICO/` (`RESEARCH.md`) | V | ALTA | BAJO |
| `RX550_Benchmarks/BENCHMARK-INVENTORY.md` *(candidato, U4)* | 2 | L195/197 `experiments/EXPLORATORIO-GravityMark/runs/…` → `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/…` | V | ALTA | BAJO |

---

## 4. SET H — análisis individual por script (NO se modifica todavía)

Conteo exacto por `grep`: **8 scripts con ruta absoluta operativa** + **2 scripts con comentario ilustrativo**
(= 10 archivos; la auditoría FASE 1–6 lo listó como "9 archivos/13 ediciones" — corregido por conteo directo).

### 4.1 Scripts con ruta absoluta usada en ejecución

| # | Script | Por qué ruta absoluta | ¿Usada en ejecución? | ¿Relativa segura? | ¿Desde dónde se ejecuta normalmente? | ¿Riesgo PYTHONPATH/imports? | Propuesta exacta antes → después | Prueba estática (sin ejecutar) |
|---|---|---|---|---|---|---|---|---|
| 1 | `FASE-R4B-GOVERNOR/telemetry/telemetria.sh` | Default de salida para correr desde cualquier CWD | **SÍ** (solo cuando no se pasa 2º arg; L13/34) | **SÍ**: `"$(dirname "$0")/../results/telemetria.csv"` | Cualquier CWD (sysfs absolutos, no depende de CWD) | Ninguno (bash puro) | `OUT=${2:-/home/lucas/…/RX550_Iterative_Research/experiments/FASE-R4B-GOVERNOR/results/telemetria.csv}` → `OUT=${2:-"$(dirname "$0")/../results/telemetria.csv"}` | `bash -n`; `realpath -m` del destino == `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/results/telemetria.csv` **(verificado)**, `results/` existe |
| 2 | `EXPLORATORIO-GravityMark/telemetria.sh` | Idem | **SÍ** | **SÍ**: `"$(dirname "$0")/runs/telemetria.csv"` | Cualquier CWD | Ninguno | `OUT=${2:-…/experiments/EXPLORATORIO-GravityMark/runs/telemetria.csv}` → `OUT=${2:-"$(dirname "$0")/runs/telemetria.csv"}` | `bash -n`; `realpath` == `runs/telemetria.csv` **(verificado)**, `runs/` existe |
| 3 | `ep06-…/soak-probe.sh` | Reutiliza helpers de la FASE B (`sampler.sh`) desde otro experimento | **SÍ** (`bash $SCR/sampler.sh …`) | **SÍ**: `SCR="$(cd "$(dirname "$0")/../fase-b-cap-probe-20260919-122038/scripts" && pwd)"` | CWD-independiente (usa `SCR` absoluto) | Ninguno | `SCR=/home/lucas/…/experiments/fase-b-cap-probe-20260919-122038/scripts` → `SCR="$(cd "$(dirname "$0")/../fase-b-cap-probe-20260919-122038/scripts" && pwd)"` | `bash -n`; `realpath` **verificado**; `ls sampler.sh` (existe, 1315 B) |
| 4 | `ep06-…/soak-final.sh` | Ídem (`run_one.sh`) | **SÍ** (`bash $SCR/run_one.sh …`) | **SÍ** (misma regla) | Ídem | Ninguno | Mismo antes → después que #3 | `bash -n`; `ls run_one.sh` (existe, 787 B); `realpath` verificado |
| 5 | `FASE-D-…/runs/etapa2/orquestador.sh` | `WORK` = raíz del repo viejo; de él derivan `BASE`, telemetría EXPLORATORIO y `cd` a WORKLOAD-SINTETICO | **SÍ** (L5-12, 29, 98, 105, 115, 122-134…) | **SÍ**: `WORK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"` → `03-EXPERIMENTOS`; luego `BASE=${WORK}/FASE-D-COUNTERS-AUDIT/runs/etapa2`, telemetría `${WORK}/EXPLORATORIO-GravityMark/telemetria.sh`, `cd ${WORK}/WORKLOAD-SINTETICO` | Cualquier CWD (paths absolutos) | Ninguno (bash; sin imports ni PYTHONPATH) | `WORK=/home/lucas/Escritorio/RX550_Iterative_Research` → `WORK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"` + ajustes en los usos derivados (L29/98/105/115). **L76 `cd /home/lucas/Escritorio/berchmark/…` NO se toca (externa D)** | `bash -n`; `realpath` de nuevos targets: `BASE`==`runs/etapa2` **(verificado)**, telemetría y WORKLOAD-SINTETICO existen |
| 6 | `FASE-D-…/runs/etapa2/analizar_etapa2.py` | `BASE` = directorio de datos (runs/etapa2) | **SÍ** (`BASE` en lecturas A1..B3) | **SÍ**: `BASE = os.path.dirname(os.path.abspath(__file__))` (el py vive junto a los datos) | Cualquier CWD | Bajo (solo stdlib; PYTHONPATH irrelevante) | `BASE = "/home/lucas/…/experiments/FASE-D-COUNTERS-AUDIT/runs/etapa2"` → `BASE = os.path.dirname(os.path.abspath(__file__))` | `python3 -m py_compile` (compila, no ejecuta); `realpath dirname` == `runs/etapa2`; presentes `telemetria.csv`/`radeontop.csv`/`umr_samples.csv` en A1..B3 |
| 7 | `FASE-D-…/runs/etapa2/auditoria_reconstruccion.py` | Ídem | **SÍ** | **SÍ** (misma regla) | Ídem | Bajo | Ídem que #6 | `python3 -m py_compile`; realpath; existencia de datos |
| 8 | `R-14-SUPERPOSITION-DISSECTION/run_superposition.sh` | `OUTDIR` default + telemetría absoluta del EXPLORATORIO | **SÍ** (OUTDIR en mkdir/redirects; telemetría en background) | **SÍ**: `OUTDIR=${2:-"$(dirname "$0")/runs/superposition_…"}` · telemetría `"$(dirname "$0")/../EXPLORATORIO-GravityMark/telemetria.sh"` | Cualquier CWD | Ninguno | L6 `OUTDIR=${2:-/home/lucas/…/experiments/R-14-SUPERPOSITION-DISSECTION/runs/…}` → `OUTDIR=${2:-"$(dirname "$0")/runs/superposition_$(date +%Y%m%d_%H%M%S)"}` · L15 telemetría → `"$(dirname "$0")/../EXPLORATORIO-GravityMark/telemetria.sh $DUR "$TELEMETRY_OUT" &` · **L19 `cd /home/lucas/Escritorio/berchmark/…` NO se toca (D)** | `bash -n`; `realpath` telemetría **(verificado: existe)**; `ls runs/` (existe) |

### 4.2 Scripts con comentario ilustrativo (NO se modifican; clasificados en §1E)

`FASE-R4B-THERMAL-TEST/run_thermal_replicate.sh:6` y `FASE-R4C-JITTER-OBSERVABILITY/harness/run_all.sh:3`.

### 4.3 Observaciones transversales del Set H

- Los scripts #1-4, #8 pertenecen a **experimentos completados** (EP-06, R-14, FASE B/R-4B); su ruta solo
  importa si se re-ejecutan. Además #3/#4 dependen de un marcador transitorio
  (`/tmp/opencode/ep06_base.txt`) → no son re-ejecutables tal cual hoy, con o sin parche. **Prioridad BAJA.**
- Los scripts #5-7 (FASE D Etapa 2) son el harness de la Etapa 2 **ejecutada** y la base de la Etapa 3
  (diseñada, NO autorizada). El parche es relevante solo si se autoriza re-ejecución/replicación (**U3**).
- En ningún caso se modifica `~/rx550-torneo`, `~/bin/rx550-torneo`, `~/rx550-power-sweep*.sh[.bak]`.

---

## 5. Cambios que NO deben realizarse (categorías C/D/F)

| Categoría | Qué | Por qué |
|---|---|---|
| C — históricos/inmutables | `REORGANIZATION-AUDIT.md` (1.258 refs), `REGISTRO-DE-MOVIMIENTOS.md`, `REORGANIZACION-MANIFEST.sha256` (1.645 hashes), `00-INDICE/README.md` solo si se depreca (U1) | Registran el estado pre-movimiento; su valor depende de las rutas originales |
| C — artefactos de datos | logs, CSV/TSV, `state_*.txt` (sysfs), snapshots, `harness/build/*`, `runs/`, telemetrías, `m1-schedule.json`, manifests internos (ep05, `frozen.sha256`, `DOWNLOAD-MANIFEST.sha256`) | Evidencia; las rutas dentro son el dato |
| D — externas deliberadas | `berchmark/` e instalados Unigine (incl. `cd …/berchmark/…` en `orquestador.sh:76` y `run_superposition.sh:19`), `~/Escritorio/RX550_Benchmarks/…` histórico, `BENCHMARK-INVENTORY.md` (salvo U4) | Dependen de la ubicación externa original |
| D — launchers HOME | `~/rx550-torneo` (bash v1), `~/bin/rx550-torneo` (bash v2), `~/rx550-power-sweep*.sh[.bak]`, `~/bench-mesa-rx550/`, `~/mesa-26.2.2-build/` | Software/scripts legados del sistema; nunca movidos |
| F — sistema y externo | `/opt/mesa-26.2.2-rx550-haswell`, sysfs/DRM/sysfs paths, Mesa/kernel/VBIOS/PowerPlay, NotebookLM (`~/Escritorio/RX550-INVESTIGACION-NOTEBOOKLM/`, 50 planas), `PROYECTOS_LUCAS`, exports personales | No forman parte del repo; no se tocan |
| F — backup | `/home/lucas/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/` (todas sus menciones) | Backup histórico; evidencia original |
| B — estructuralmente válidos | Launcher `rx550-torneo/rx550-torneo` (PYTHONPATH relativo a `src/`), `$HERE/src` en el launcher del torneo y `sys.path` relativo en `tests/` | No contienen rutas viejas; son el patrón correcto |
| — | Tests/lógica de `rx550-torneo` del repo, `04-IMPLEMENTACION/projects/…` | Operativos del repo; sin refs viejas |

---

## 6. Riesgos

1. **Sustitución global (prohibida).** Un `sed`/`perl` masivo rompería refs C/D/F. Cada edición es 1:1 aprobada.
2. **Set B (mapa):** parche en bloque de un documento largo; error silencioso dejaría un mapa incoherente.
   Mitigación: solo refs cuyo destino fue verificado con `realpath`/existencia (tabla de existencias §7).
3. **Set H**: un error en la derivación relativa de `orquestador.sh` rompería un harness futuro de FASE D.
   Mitigación: prueba estática antes de aplicar + commit aparte; prioridad baja hasta decisión U3.
4. **Contradicción de índices**: editar `00-INDICE/README.md` (Set A) y luego deprecarlo (U1) sería trabajo en
   vano → resolver U1 antes de tocar ese archivo.
5. **Refs históricas tocadas por error** (p. ej. las que citan el backup `mesa-e1-…` o `/opt/…`): mitigación:
   lista explícita de NO-tocar (§5) + grep post-parche que confirma que solo quedan las permitidas.
6. **Doble mapeo FASE-R2**: `R2-GLOBAL-DOCUMENTATION-MAP.md` vive en `00-INDICE/`, mientras el resto de
   FASE-R2 quedó en `01-AUDITORIA/…` → en los parches hay que tratar ese archivo como caso especial (incluido
   en tabla de mapeo).

---

## 7. Estrategia de verificación posterior (post-parche, todo estático)

1. **Destinos:** verificación anticipada ya realizada en FASE 7 para los targets críticos:
   `02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt`, `POLARIS12-MAP/{POLARIS12-MAP,EXPERIMENT-CANDIDATES}.md`,
   `03-EXPERIMENTOS/{EXPLORATORIO-GravityMark/telemetria.sh, WORKLOAD-SINTETICO/{RESEARCH.md,src/compute.comp},
   M1-cap-35-30/{RESULTADOS-M1.md,runs/20260919-235939}, FASE-D-…-ETAPA-3-EVENTS.md,
   FASE-R4A-…EXP-F3-A-BANDWIDTH-REAL.md, FASE-R4B-GOVERNOR/harness/build/governor_harness}`,
   `01-AUDITORIA/AUDIT-001/METRICS-DEFINITIONS.md`, `FASE-R3-1-…/FUSION-01-….md`,
   `05-FUENTES-EXTERNAS/FASE-R0-…/R0-1-GFX8-EVENT-ID-REFERENCE.txt`,
   `04-IMPLEMENTACION/projects`, `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` — **todos existen (OK)**.
   Los targets restantes se verifican con `realpath -m` + `test -e` en el mismo commit.
2. **Grep inverso:** por set, `grep -nE 'RX550_Iterative_Research|experiments/|~/Escritorio'` sobre los
   archivos editados → cero coincidencias, excepto las C/D/F documentadas en §5.
3. **Scripts:** `bash -n` (6 shells), `python3 -m py_compile` (2 py), `grep` de prefijo viejo en los 8 = 0,
   listados de dependencias (sampler.sh/run_one.sh/telemetria.sh) antes/después idénticos.
4. **Git:** `git diff --stat` limitado a la lista exacta (§8) · commit por conjunto A→H · `git status` limpio ·
   hashes (`sha256sum`) de archivos **no objetivo** inalterados (logs, manifests, scripts no parcheados).
5. **Nada se ejecuta:** sin benchmarks, sin scripts, sin sysfs, sin cambios de sistema; la verificación es
   exclusivamente estática + diff.

---

## 8. Lista exacta de archivos que serían modificados

**(46 obligatorios + 4 opcionales; pendiente decisión U1–U5 y aprobación final.)**

| Set | Archivos | Condición |
|---|---|---|
| **A** | `MASTER-RESEARCH-STATUS.md` · `MASTER-PLAN.md` · `README.md` (índice legado) · `PROJECT-DOCUMENTATION-STATUS.md` · `FINAL-RESEARCH-STATUS.md` · `decisions.md` · `experiments_proposed.md` | `README.md` solo si U1=índice activo; MASTER-PLAN:781 opcional (U5) |
| **B** | `R2-GLOBAL-DOCUMENTATION-MAP.md` | Según U2 (vivo completo o nuevo mapa) |
| **C** | `AUDIT-001.md` · `FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/README.md` · `FUSION-03-…md` · `FASE-R3-FINAL-REPORT.md` · `FASE-R2-FINAL-REPORT.md` · `R2-HISTORICAL-EXPERIMENT-INVENTORY.md` · `FASE-R1-FINAL-REPORT.md` · `R1-1-GFX8-EVENT-RECONCILIATION.md` | — |
| **D** | `02-ARQUITECTURA/research_log.md` · `02-ARQUITECTURA/evidence.md` | — |
| **E** | `EXP-F4-A-PROTOCOL.md` · `EXP-F4-A-PROTOCOL-v2.2.md` · `TEST-TERMICO-READONLY.md` · `PRECHECK-REPORT.md` · `EXP-F1-A-RESULTADOS.md` · `R-14-SUPERPOSITION-DISSECTION.md` · `FASE-D-ETAPA-2-PLAN.md` · `FASE-D-ETAPA-3-PRECHECK.md` · `FASE-D-GFX8-EVENT-ID-AUDIT.md` · `WORKLOAD-SINTETICO/RESEARCH.md` · `M1-cap-35-30/RESULTADOS-M1.md` · `WORKLOAD-SINTETICO/runs/exploratorio-01/RESULTADO-EXPLORATORIO-01.md` | — |
| **F** | `rx550-torneo/README-FASE1.md` · `README-FASE2.md` · `README-FASE3.md` · `SYNTHETIC-WORKLOAD-DESIGN.md` · `FASE-E-REAL-GAME-BASELINE-DESIGN.md` · `FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md` | — |
| **G** | `FASE-R0-EXTERNAL-KNOWLEDGE-FINAL-REPORT.md` · `R0-2-POWERPLAY-MCLK-SMU7.md` | `RX550_Benchmarks/BENCHMARK-INVENTORY.md` solo si U4=SÍ |
| **H** | `telemetria.sh` (FASE-R4B) · `telemetria.sh` (EXPLORATORIO) · `soak-probe.sh` · `soak-final.sh` · `orquestador.sh` · `analizar_etapa2.py` · `auditoria_reconstruccion.py` · `run_superposition.sh` | Comentarios (`run_thermal_replicate.sh`, `harness/run_all.sh`) solo cosmética autorizada; prioridad según U3 |

**No se modifica** ningún archivo de las categorías C/D/F (§5) ni se crea otro archivo distinto de este plan
hasta nueva autorización.
