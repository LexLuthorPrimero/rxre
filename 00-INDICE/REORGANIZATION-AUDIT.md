# REORGANIZATION-AUDIT.md — Auditoría completa previa a reorganización documental (RX 550)

**Fecha:** 2026-09-23 · **Modo:** SOLO LECTURA / AUDITORÍA
**Regla de fase:** NO se movió, renombró, borró, copió ni modificó ningún archivo del sistema ni del proyecto. La raíz futura `~/Escritorio/RX550-INVESTIGACION/` NO fue creada. Toda la política de la sección 14 del encargo se respetó.
**Documento nuevo:** este archivo es la única creación de esta fase (autorizado por el encargo, §15).

---

## 1. Estado actual

Se detectaron **8 zonas** RX550 fuera de una única raíz + 3 temporales + artefactos de build:

| Zona | Ubicación | Contenido | Función |
|---|---|---|---|
| Repo de trabajo | `~/Escritorio/RX550_Iterative_Research/` | 172 `.md`, 1.256 archivos, 36M (experiments) + 448K (rx550-torneo) + 408K (projects) | Raíz de trabajo actual (no oficial) |
| NotebookLM | `~/Escritorio/RX550-INVESTIGACION-NOTEBOOKLM/` | 50 archivos planos (copias exactas) | Curaduría NotebookLM (carpeta oficial futura) |
| Benchmarks | `~/Escritorio/RX550_Benchmarks/` | inventario + manifests + 1 descarga + 1 partial | Fuentes externas |
| Software benchmarks | `~/Escritorio/berchmark/` | 4 `.run` + 4 árboles instalados | Software instalado (fuera de raíz) |
| Backup histórico | `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/` | 31.584 archivos (incl. `mesa-source` 29.393 f) | Histórico consolidado con SHA256SUMS |
| Proyecto histórico personal | `~/Escritorio/PROYECTOS_LUCAS/01_RX550_MODO_TORNEO/` y `02_MESA_RADV/` | SESIONES (inmutables) + 00_ESTADO | Sistema documental previo |
| Artefactos en home | `~/rx550-torneo`, `~/bin/rx550-torneo`, `~/rx550-power-sweep.sh[.bak]`, `~/rx550-power-sweep-*` (×2), `~/bench-mesa-rx550/` (vacío), `~/mesa-26.2.2-build/` | scripts legado + datos de barrido + build Mesa | Evidencia + software |
| Temporales | `/tmp/rx550f2-preflight/`, `/tmp/rx550test-7dz30078/`, `/tmp/rx550-torneo-audit/` | 2 write-tests + 1 carpeta vacía | Trabajo transitorio |

Notas: `~/Escritorio/RX550-INVESTIGACION/` **no existe**. `~/research-downloads/` **no existe**. No hay nada RX550 en `~/Documentos/` ni `~/Descargas/`. El repo actual **no está versionado** (no hay `.git`; la raíz `~/Escritorio/` es un work-tree git pero `RX550_Iterative_Research/` no está tracked).

## 2. Inventario del repositorio actual

| Área | Archivos | Tamaño | Contenido |
|---|---|---|---|
| Raíz (13 `.md` + 1 `.txt`) | 14 | ~172K | 4 documentos maestros + 8 docs de investigación + README + `RX550_BUILD_SPECIFICATION.txt` |
| `experiments/` | 108 `.md` + datos (22 carpetas) | 36M | Fases A, B, EP-05/06, R-14, D, R-0/R-1/R-2/R-3/R-3-1, R-4A/B/C, M1, WORKLOAD-SINTETICO, POLARIS12-MAP, AUDIT-001, IMPLEMENTATION-READINESS, `results/` |
| `projects/` | 47 `.md` | 408K | 14 diseños (BERRETA, GHOST, CLOSED-LOOP-QUALITY-GOVERNOR, etc.) |
| `rx550-torneo/` | 4 `.md` + código | 448K | Herramienta Python operativa (launcher 235 B + `src/` + `tests/`) |

 peso dominante: `FASE-R4B-GOVERNOR` (340 f, 20M), `FASE-R4B-THERMAL-TEST` (53 f, 6M), `FASE-R4C` (85 f, 2M), `FASE-D` (93 f, 1.9M).

## 3. Duplicados detectados

| Duplicado | Ubicación A | Ubicación B | Verificación | Estado |
|---|---|---|---|---|
| 50 docs NotebookLM | `RX550-INVESTIGACION-NOTEBOOKLM/` | originales dentro del repo | copias **exactas** (hash idéntico en 50/50) | DUPLICADO-AUDITAR → conversión a symlinks pendiente de autorización |
| `rx550-power-sweep-20260918-132309/` (194 f) | `~/` | `backup/experiments/` | IDENTICOS (`diff -rq` sin diferencias) | DUPLICADO-AUDITAR |
| `rx550-power-sweep-20260918-140527/` (194 f) | `~/` | `backup/experiments/` | IDENTICOS | DUPLICADO-AUDITAR |
| `GravityMark_1.89.run` (193.327.384 B) | `RX550_Benchmarks/official-downloads/gravitymark/` | `berchmark/` | hash `de090c7b…` en ambos | DUPLICADO-AUDITAR |
| `~/rx550-torneo` (14.229 B) | `~/` | `backup/code/rx550-torneo` | hash `bcc41451…` idéntico | DUPLICADO (copia de seguridad legítima) |
| `~/bin/rx550-torneo` (16.760 B) | `~/bin/` | `backup/code/rx550-torneo-bin-20260918` | hash `d0c25383…` idéntico | DUPLICADO (copia de seguridad legítima) |
| `~/rx550-power-sweep.sh` (12.188 B) | `~/` | `backup/code/rx550-power-sweep.sh` | hash `01f331bb…` idéntico | DUPLICADO (copia de seguridad legítima) |

**No son duplicados (son herramientas distintas):** el `rx550-torneo` del repo (launcher Python, 235 B, separado de `~/bin`) vs. los scripts bash legado del "modo torneo".

## 4. Archivos únicos (evidencia que NO debe perderse)

- **`backup/data/kalm_dataset_v2.csv`** (1.110 líneas, telemetría kalm/x 09-17/18) — citado como contexto kalm en Fase A/EP-05/EP-06.
- **`backup/data/gpu_real_data.csv`**, `backup/data/diagnostico_pc.txt`, `backup/data/_geeks3d_gputest_log.txt`, `backup/data/investigacion_mesa.txt`.
- **`backup/system/hardware-and-vulkan-snapshot.txt`** — snapshot HW/Vulkan previo.
- **`backup/audit-history/PHASE0-AUDIT-STATUS.md`** y `shell-history-rx550-kalm.txt`.
- **Experimentos históricos** del backup: `mesa-ab-results-*` (×2), `mesa-e1/e2/e3`, `mesa-p1/p2`, `mesa-resolution-*` (×2) — E1/E3 declarados NO reproducibles en el repo; el backup es su única copia.
- **`PROYECTOS_LUCAS/01_RX550_MODO_TORNEO/SESIONES/001.md`** y `00_ESTADO.md` — datos HW verificados y validación `MESA_VK_DEVICE_SELECT=1002:699f` (09-18, previos al repo actual).
- **Todo el contenido de `rx550-power-sweep-*`** (datos de barrido 09-18; referenciados en `R2-HISTORICAL-EXPERIMENT-INVENTORY.md`, `INVALIDACION-corridas-04-09.md`, `research_log.md`) — único lugar con el contexto de invalidación de `power1_input`.
- **`experiments/` del repo** — resultados verificados (D-1/2, R-4A/B/C, M1, WORKLOAD-SINTETICO, etc.).

## 5. Documentos NotebookLM (50) — mapeo completo con hash

Todos son **copias exactas** (SHA256 idéntico) de originales del repo. Columna final: sugerencia de tratamiento **mantener (M)** / **retirar (R)** *solo en términos conceptuales* (la ejecución queda pendiente de autorización; modelo elegido: symlinks).

| # | Archivo NotebookLM | SHA256 (archivo NB) | Original (repo) | Idéntico | M/R |
|---|---|---|---|---|---|
| 1 | 01-AUDIT-001.md | a4059ecb… | experiments/AUDIT-001/AUDIT-001.md | SÍ | M |
| 2 | 01-EXP-F3-A-BANDWIDTH-REAL.md | ac86e5cc… | experiments/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md | SÍ | M |
| 3 | 01-EXP-F4-A-PROTOCOL.md | b9040cc7… | experiments/FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL.md | SÍ | M |
| 4 | 01-FASE-D-COUNTERS-AUDIT.md | 7f40cfd7… | experiments/FASE-D-COUNTERS-AUDIT/FASE-D-COUNTERS-AUDIT.md | SÍ | M |
| 5 | 01-FASE-R0-FINAL-REPORT.md | 66d3838c… | experiments/FASE-R0-EXTERNAL-KNOWLEDGE/FASE-R0-EXTERNAL-KNOWLEDGE-FINAL-REPORT.md | SÍ | M |
| 6 | 01-FASE-R1-FINAL-REPORT.md | 0c2a833d… | experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/FASE-R1-FINAL-REPORT.md | SÍ | M |
| 7 | 01-FASE-R2-FINAL-REPORT.md | da46de04… | experiments/FASE-R2-PROJECT-DOCUMENTATION/FASE-R2-FINAL-REPORT.md | SÍ | M |
| 8 | 01-R-14-SUPERPOSITION-DISSECTION.md | a584e981… | experiments/R-14-SUPERPOSITION-DISSECTION/R-14-SUPERPOSITION-DISSECTION.md | SÍ | M |
| 9 | 01-README.md | 9616f750… | README.md (raíz) | SÍ | M |
| 10 | 01-RESULTADOS-FASE-B.md | 8b2b32d6… | experiments/fase-b-cap-probe-20260919-122038/RESULTADOS-FASE-B.md | SÍ | M |
| 11 | 02-EP08-auditoria-telemetria-E1E3.md | cfeba37f… | experiments/fase-b-cap-probe-20260919-122038/EP08-auditoria-telemetria-E1E3.md | SÍ | M |
| 12 | 02-ERRATA.md | 28d10bc2… | experiments/AUDIT-001/ERRATA.md | SÍ | M |
| 13 | 02-EXP-F4-A-PROTOCOL-v2.2.md | d51b29d6… | experiments/FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL-v2.2.md | SÍ | M |
| 14 | 02-FASE-D-ETAPA-2-RESULTADOS.md | 444efd11… | experiments/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-RESULTADOS.md | SÍ | M |
| 15 | 02-MASTER-PLAN.md | 750a162a… | MASTER-PLAN.md | SÍ | M |
| 16 | 02-R0-1-GFX8-EVENT-IDS.md | 0307efeb… | experiments/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-IDS.md | SÍ | M |
| 17 | 02-R1-6-EVIDENCE-STATE-MODEL.md | e8d36fc3… | experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/R1-6-EVIDENCE-STATE-MODEL.md | SÍ | M |
| 18 | 02-R2-GLOBAL-DOCUMENTATION-MAP.md | 31fdf9e1… | experiments/FASE-R2-PROJECT-DOCUMENTATION/R2-GLOBAL-DOCUMENTATION-MAP.md | SÍ | M |
| 19 | 02-RESULTADO-Superposition.md | 99069e78… | experiments/EXPLORATORIO-GravityMark/runs/RESULTADO-Superposition.md | SÍ | M |
| 20 | 03-EVIDENCE-MATRIX.md | 8d66bd47… | experiments/AUDIT-001/EVIDENCE-MATRIX.md | SÍ | M |
| 21 | 03-EXP-F4-A-PROTOCOL-v2.3.md | c38095b8… | experiments/FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL-v2.3.md | SÍ | M |
| 22 | 03-FASE-D-GFX8-EVENT-ID-AUDIT.md | e1981649… | experiments/FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md | SÍ | M |
| 23 | 03-FASE-R3-FINAL-REPORT.md | 330c107e… | experiments/FASE-R3-NOVELTY-AUDIT/FASE-R3-FINAL-REPORT.md | SÍ | M |
| 24 | 03-MASTER-RESEARCH-STATUS.md | e65893f3… | MASTER-RESEARCH-STATUS.md | SÍ | M |
| 25 | 03-POLARIS12-MAP.md | 6562137d… | experiments/POLARIS12-MAP/POLARIS12-MAP.md | SÍ | M |
| 26 | 03-R0-2-POWERPLAY-MCLK-SMU7.md | a1787755… | experiments/FASE-R0-EXTERNAL-KNOWLEDGE/R0-2-POWERPLAY-MCLK-SMU7.md | SÍ | M |
| 27 | 03-R1-7-CRITICAL-GAPS.md | 410f94de… | experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/R1-7-CRITICAL-GAPS.md | SÍ | M |
| 28 | 04-EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md | dab1afeb… | experiments/FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md | SÍ | M |
| 29 | 04-FINAL-RESEARCH-STATUS.md | dfdc4571… | FINAL-RESEARCH-STATUS.md | SÍ | M |
| 30 | 04-R0-1-GFX8-EVENT-ID-REFERENCE.txt | 3528b548… | experiments/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-ID-REFERENCE.txt | SÍ | M |
| 31 | 04-R3-1-MASTER-REPORT.md | 4f65c068… | experiments/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/R3-1-MASTER-REPORT.md | SÍ | M |
| 32 | 04-RESULTADOS-FASE-A.md | 5932a123… | experiments/fase-a-discriminacion-20260919-114241/RESULTADOS-FASE-A.md | SÍ | M |
| 33 | 04-UNVERIFIED-CLAIMS.md | d34d8273… | experiments/POLARIS12-MAP/UNVERIFIED-CLAIMS.md | SÍ | M |
| 34 | 05-EXP-F4-A-RESULTADOS.md | 0bf12865… | experiments/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS.md | SÍ | M |
| 35 | 05-INVALIDACION-corridas-04-09.md | a0bc7e3b… | experiments/fase-a-discriminacion-20260919-114241/INVALIDACION-corridas-04-09.md | SÍ | M |
| 36 | 05-PROJECT-DOCUMENTATION-STATUS.md | 438493db… | PROJECT-DOCUMENTATION-STATUS.md | SÍ | M |
| 37 | 05-R3-NOVELTY-MATRIX.md | b503c0b0… | experiments/FASE-R3-NOVELTY-AUDIT/R3-NOVELTY-MATRIX.md | SÍ | M |
| 38 | 06-AUDITORIA-PRE-RUN-v2.3.md | 75cc71de… | experiments/FASE-R4B-GOVERNOR/AUDITORIA-PRE-RUN-v2.3.md | SÍ | M |
| 39 | 06-knowledge.md | 287e9d25… | knowledge.md | SÍ | M |
| 40 | 07-evidence.md | 44e7d300… | evidence.md | SÍ | M |
| 41 | 07-PRE-FLIGHT-CALIBRACION-EXP-F4-A.md | faa0165e… | experiments/FASE-R4B-GOVERNOR/PRE-FLIGHT-CALIBRACION-EXP-F4-A.md | SÍ | M |
| 42 | 08-hypotheses.md | 49862cbd… | hypotheses.md | SÍ | M |
| 43 | 08-RESULTADOS-MINITEST-7.3-B.md | 5fe95792… | experiments/FASE-R4B-THERMAL-TEST/RESULTADOS-MINITEST-7.3-B.md | SÍ | M |
| 44 | 09-decisions.md | 16fdc2b9… | decisions.md | SÍ | M |
| 45 | 09-TEST-TERMICO-READONLY.md | 18813caa… | experiments/FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md | SÍ | M |
| 46 | 10-open_questions.md | 313e11a2… | open_questions.md | SÍ | M |
| 47 | 10-RESULTADOS-TEST-TERMICO.md | 8ad276a5… | experiments/FASE-R4B-THERMAL-TEST/RESULTADOS-TEST-TERMICO.md | SÍ | M |
| 48 | 11-EXP-F4-A-MINITEST-RAMP-GOV-PLAN.md | fd894140… | experiments/FASE-R4B-THERMAL-TEST/EXP-F4-A-MINITEST-RAMP-GOV-PLAN.md | SÍ | M |
| 49 | 11-rejected_ideas.md | 415063f9… | rejected_ideas.md | SÍ | M |
| 50 | 12-research_log.md | f572fbab… | research_log.md | SÍ | M |

Observaciones:
- `01-FASE-R0-FINAL-REPORT.md` y `01-README.md` tuvieron que resolverse manualmente (nombre ≠ basename del original); verificados por hash.
- Los 50 archivos **necesitan conservar su nombre actual** en la carpeta NotebookLM (prefijo numérico = orden de carga); como symlinks, el nombre del enlace será ese mismo.
- La fuente de verdad será el **original del proyecto**; la carpeta NotebookLM solo contendrá enlaces (plana, ≤50).
- **Riesgo identificado:** el flujo de carga de NotebookLM debe aceptar symlinks; verificación obligatoria antes de reemplazar las copias (si falla, se detiene y se propone alternativa, sin improvisar).

## 6. Scripts duplicados (hash, versión y relación)

| Script | SHA256 | Tamaño | Fecha | Rol / versión |
|---|---|---|---|---|
| `~/rx550-torneo` | bcc41451dac63b18ea450e9f7ad75f0da52a6a4187a1f927fc61b3862689269f | 14.229 B | 09-18 12:43 | Legado "modo torneo" v1 (bash) — idéntico a `backup/code/rx550-torneo` |
| `~/bin/rx550-torneo` | d0c253839c3d427a272a3d47651b33b83ce5b4c84e235b4c9b8aa0347f1f892f | 16.760 B | 09-18 16:12 | Legado "modo torneo" v2 (bash, 2,5 KB mayor) — idéntico a `backup/code/rx550-torneo-bin-20260918` |
| `repo rx550-torneo/rx550-torneo` | 4b05d8c616f67e092daa24f71fc5158f2d4331a23518a2ba8dcff153e52c64f2 | 235 B | 09-19 22:02 | **Herramienta operativa actual** — launcher del CLI Python (`exec python3 -m rx550_torneo.cli`, `PYTHONPATH` relativo a `src/`) |
| `~/rx550-power-sweep.sh` | 01f331bb9f311445ac905c054941d749d03f34013d092a9bb34436a85690051a | 12.188 B | 09-18 13:58 | Barrido power cap (vigente) — idéntico a `backup/code/rx550-power-sweep.sh` |
| `~/rx550-power-sweep.sh.bak` | 0b8a985e53123d94b661b36c7ada75603b48d68b612ccf70f4bb2fa661204c9d | 11.432 B | 09-18 13:17 | Versión anterior del barrido (756 B menor) |

Conclusión: la herramienta **operativa** es el CLI Python del repo. Los 4 scripts bash (2 familias × 2 versiones) son **históricos** y ya están respaldados en el backup consolidado. Propuesta: conservar-los donde están y referenciarlos desde `04-IMPLEMENTACION/` (sin moverlos).

## 7. Datos experimentales

- **En el repo:** `experiments/` completo (Fase A/B/EP/R-14/D/R-4A/B/C/M1/WORKLOAD-SINTETICO, `results/`) — integridad verificada por las fases R-0/R-1 (estados de evidencia).
- **Fuera del repo (home):** 2 carpetas `rx550-power-sweep-*` (194 f c/u) = **duplicados exactos** de las existentes en el backup. Referenciadas en el repo (R2-históricos, INVALIDACION, research_log). Asociación: contexto previo a Fase A (18/09), precursor de la invalidación `power1_input`.
- **Dentro del backup:** experimentos históricos 17/09 (mesa-ab/e1/e2/e3/resolution/p1/p2) + los power-sweep + `kalm_dataset_v2.csv` (evidencia única).

## 8. Fuentes externas

| Elemento | Ubicación | Tipo | Nota |
|---|---|---|---|
| BENCHMARK-INVENTORY.md (35 KB) | `RX550_Benchmarks/` | documento | inventario de candidatos M2 |
| DOWNLOAD-MANIFEST.sha256 + SOURCES-AND-EXECUTION.md | `RX550_Benchmarks/docs/` | manifiesto | hash de la descarga oficial |
| GravityMark_1.89.run (193 MB) | `RX550_Benchmarks/official-downloads/gravitymark/` | descarga | duplicado con `berchmark/` (mismo hash `de090c7b…`) |
| Unigine_Superposition-1.1.run.partial (34 MB) | `RX550_Benchmarks/cancelled-downloads/` | descarga cancelada | conservada sin ejecutar |
| `official-downloads/unigine/` | vacío | reservado | |
| FASE-R0-EXTERNAL-KNOWLEDGE (8 f) | repo `experiments/` | análisis de fuentes | R0-1..R0-6 + REFERENCE.txt (GPUPerfAPI v3.11.1) |
| `berchmark/` (4 `.run` + 4 instalados) | `~/Escritorio/berchmark/` | **software instalado** | GravityMark/Superposition/Heaven/Valley — fuera de la raíz documental; ya referenciado por PROJECT-DOCUMENTATION-STATUS |
| `nootbooklm.txt` (7 KB, en `~/Escritorio/`) | export | material fuente para NotebookLM | se registra como exclusión (§11) |

Política aplicable: `UNKNOWN → fuente → evidencia → resultado → limitación → estado`. Los UNKNOWNs activos están en `open_questions.md` y `R1-7-CRITICAL-GAPS.md`; **no existe aún** `FUENTES-FALTANTES.md` (propuesta: crearlo en `00-INDICE/` durante la reorganización, no ahora).

## 9. Backups y proyectos históricos

| Elemento | Contenido | Relación con el repo actual |
|---|---|---|
| `RX550_Modo_Torneo_Backup_2026-09-19_0836/` (31.584 f; 5.4 MB de manifest/SHA256SUMS crítico) | experiments históricos 17-18/09, `code/` (23 scripts), `data/` (kalm_dataset_v2.csv etc.), `etc/` (kalm units/rules), `system/`, `audit-history/`, `mesa/mesa-source` (29.393 f) | **Predecesor consolidado** del repo actual; fuente única de los históricos E1/E3 y kalm. Debe permanecer en lugar y registrarse como `DOCUMENTO-ANTERIOR → SUSTITUTO = RX550_Iterative_Research` |
| `PROYECTOS_LUCAS/01_RX550_MODO_TORNEO/` | SESIONES/001.md (inmutable) + `00_ESTADO.md` (fotografía mutable) + DATOS/ (vacío) | Sistema documental personal 09-18; evidencia única: datos HW verificados. Permanecer en lugar |
| `PROYECTOS_LUCAS/02_MESA_RADV/` | 00_ESTADO.md + SESIONES | Histórico relacionado con Mesa/RADV. Permanecer en lugar |

## 10. Temporales

| Ubicación | Contenido | Veredicto |
|---|---|---|
| `/tmp/rx550f2-preflight/rx550-torneo/write-test-20260919-224316.json` | 8 KB, write-test de preflight | SIN evidencia única → proponer descarte (requiere decisión) |
| `/tmp/rx550test-7dz30078/` | vacío | descartable |
| `/tmp/rx550-torneo-audit/write-test-20260919-224612.json` | 8 KB, write-test | SIN evidencia única → proponer descarte (requiere decisión) |

## 11. Exportaciones y chats (`~/Escritorio/*.txt`)

| Archivo | Tamaño | Contenido estimado | Clasificación |
|---|---|---|---|
| documentos1.txt | 346.456 B | Transcript de conversación de investigación RX550 (incluye la sesión actual `ses_f4609…`) | CONTEXTO-HISTÓRICO |
| chatgpt.txt | 155.367 B | Export ChatGPT sobre verificación RX550 | CONTEXTO-HISTÓRICO |
| kimi.txt | 226.043 B | Export Kimi | CONTEXTO-HISTÓRICO |
| opencode.txt | 450.129 B | Export OpenCode | CONTEXTO-HISTÓRICO |
| opencode2.txt | 650.144 B | Export OpenCode | CONTEXTO-HISTÓRICO |
| nootbooklm.txt | 7.029 B | Nota técnica/prompt para NotebookLM | FUENTE-ORIGINAL (material fuente) |
| honey selec.txt | 26 B | sin contenido relevante aparente | NO-RELACIONADO |
| discord.txt | 17 B | sin contenido relevante aparente | NO-RELACIONADO |

Tratamiento: **no se mueven ni se incorporan** a la raíz; se registran como exclusión. Si en una fase futura una afirmación solo existiera aquí, se extrae únicamente lo necesario hacia la documentación oficial (regla del encargo).

## 12. Builds

| Artefacto | Tamaño | Tratamiento |
|---|---|---|
| `~/mesa-26.2.2-build/` | ~656 MB (árbol fuente + build) | **Fuera de la raíz documental**; permanece donde está; se registrará en el índice como artefacto externo (tamaño, ubicación, propósito: build Mesa usado en EP-05) |
| `backup/mesa/mesa-source/` (29.393 f) | — | Dentro del backup histórico; no se toca |

## 13. Mapeo propuesto hacia `~/Escritorio/RX550-INVESTIGACION/`

> Propuesta (no ejecutada). La estructura oficial futura: `00-INDICE/`, `01-AUDITORIA/`, `02-ARQUITECTURA/`, `03-EXPERIMENTOS/`, `04-IMPLEMENTACION/`, `05-FUENTES-EXTERNAS/`, `README.md`. La carpeta NotebookLM queda **independiente** de esta raíz (plana, sin subcarpetas).

| Origen | Destino propuesto | Tipo | Acción propuesta |
|---|---|---|---|
| `experiments/FASE-R1`,`FASE-R2`,`FASE-R3`,`FASE-R3-1`,`AUDIT-001` | `01-AUDITORIA/` | auditoría | MOVER (compatible con refs internas; ver §14) |
| `experiments/FASE-R0` | `05-FUENTES-EXTERNAS/` | fuentes externas analizadas | MOVER (REQUIERE-DECISION: alternativa 01-AUDITORIA) |
| `experiments/IMPLEMENTATION-READINESS/IMPLEMENTATION-READINESS-AUDIT.md` | `01-AUDITORIA/` | auditoría de madurez | MOVER |
| `experiments/FASE-R4A`, `R4B`, `R4C`, `D`, `R-14`, `M1`, `fase-a`, `fase-b`, `ep05`, `ep06`, `WORKLOAD-SINTETICO`, `EXPLORATORIO-GravityMark`, `results` | `03-EXPERIMENTOS/` | experimentos | MOVER (mantener estructura interna) |
| `experiments/POLARIS12-MAP` | `02-ARQUITECTURA/` | mapa HW/SW | MOVER (REQUIERE-DECISION) |
| `projects/` (14) | `04-IMPLEMENTACION/` | diseños | MOVER |
| `rx550-torneo/` (repo) | `04-IMPLEMENTACION/` | herramienta operativa | MOVER |
| `experiments/FASE-R2-PROJECT-DOCUMENTATION/FASE-{E,F,G,H,I,K,L,M,N,O,P,Q}-DESIGN.md` + `EXPERIMENT-PRIORITY-MATRIX` | `04-IMPLEMENTACION/` (diseños) | diseño | MOVER (REQUIERE-DECISION: desglosar vs. mantener unidad R2) |
| Raíz: `MASTER-PLAN`, `MASTER-RESEARCH-STATUS`, `PROJECT-DOCUMENTATION-STATUS`, `FINAL-RESEARCH-STATUS`, `decisions` | `00-INDICE/` | estado/índice | MOVER (REQUIERE-DECISION) |
| Raíz: `knowledge`, `evidence`, `hypotheses`, `open_questions`, `rejected_ideas`, `research_log`, `experiments_proposed` | `02-ARQUITECTURA/` (conocimiento) | conocimiento | MOVER (REQUIERE-DECISION) |
| `RX550_BUILD_SPECIFICATION.txt` | `02-ARQUITECTURA/` | especificación | MOVER |
| `~/rx550-power-sweep-*` (datos) | `03-EXPERIMENTOS/` (histórico) | evidencia | MOVER (tras resolver duplicado home/backup) |
| `RX550_Benchmarks/` + `R0-1-GFX8-EVENT-ID-REFERENCE.txt` | `05-FUENTES-EXTERNAS/` | fuentes | MOVER |
| Scripts legado (`~/rx550-torneo`, `~/bin/rx550-torneo`, `~/rx550-power-sweep.sh[.bak]`) | — | histórico/software | CONSERVAR-EN-LUGAR + referencia desde `04-IMPLEMENTACION/` |
| `~/mesa-26.2.2-build/` | — | build | CONSERVAR-EN-LUGAR + registrar en índice |
| `RX550_Modo_Torneo_Backup_…` | — | backup histórico | CONSERVAR-EN-LUGAR + registrar relación |
| `PROYECTOS_LUCAS/01_RX550_MODO_TORNEO` y `02_MESA_RADV` | — | histórico personal | CONSERVAR-EN-LUGAR + registrar |
| `berchmark/` (software instalado) | — | software | CONSERVAR-EN-LUGAR (ya referenciado) |
| `RX550-INVESTIGACION-NOTEBOOKLM/` (50) | — | curaduría | NO-MOVER ahora; conversión a symlinks pendiente de autorización y verificación del flujo |
| `/tmp/rx550*` | — | temporal | NO-MOVER; proponer descarte (decisión) |
| `~/Escritorio/*.txt` (8 exportes) | — | material fuente/histórico | EXCLUIR + registrar exclusiones |
| `~/bench-mesa-rx550/` | — | vacío | NO-MOVER (registrar estado) |

## 14. Riesgos

1. **Falta de control de versiones:** el repo no está en git → cualquier movimiento sin registro previo de hash es irreversible en la práctica. Mitigación: todos los movimientos llevan hash+registro, y se propone inicializar un git en la nueva raíz (decisión §16).
2. **Referencias cruzadas internas (alta):** `MASTER-RESEARCH-STATUS`, `PROJECT-DOCUMENTATION-STATUS`, `README`, `research_log`, `R2-GLOBAL-DOCUMENTATION-MAP` y los informes FASE citan rutas del patrón actual `experiments/FASE-…` (p. ej. `FASE-R4B-GOVERNOR/results/v23/…`). Mover carpetas rompe esas rutas. Mitigación: actualizar referencias en cada doc movido + registrar `ubicación original → nueva` en `REGISTRO-DE-MOVIMIENTOS.md`.
3. **Manifiestos y datos (media):** FASE-R4B (340 f, 20M) y THERMAL-TEST (53 f, 6M) contienen manifiestos con rutas internas relativas; al mover el contenedor, las rutas relativas se preservan (riesgo bajo) pero las absolutas citadas en informes quedan obsoletas.
4. **Scripts (media):** el launcher `rx550-torneo` del repo usa `HERE="$(cd "$(dirname …)" && pwd)"`; su ejecución se preserva al mover la carpeta completa. Cualquier config citando `~/` o rutas absolutas se rompería.
5. **NotebookLM (alta si se convierte):** el cargador debe aceptar symlinks; las copias actuales funcionan con seguridad. Verificación obligatoria antes del reemplazo; si falla → parar y proponer alternativa.
6. **Desglose FASE-R2 (media):** mover los FASE-E…Q-DESIGN fuera de `FASE-R2-PROJECT-DOCUMENTATION` rompe la unidad de la fase R-2 y sus referencias en `R2-GLOBAL-DOCUMENTATION-MAP.md` y `PROJECT-DOCUMENTATION-STATUS.md`.
7. **Duplicado power-sweep (baja):** home y backup son idénticos; decidir cuál es fuente de verdad antes de mover.
8. **Composición del conteo:** "mover una carpeta" del repo conlleva tipos mezclados (md + csv + logs + manifiestos); la regla impide tratar la carpeta como homogénea, por eso cada grupo tiene su tipo declarado en §13.

## 15. Referencias que podrían romperse (inventario de rutas citadas)

- Rutas en `README.md` (raíz): `experiments/fase-a-…`, `fase-b-…`, `ep06-…`, `ep05-…`, `M1-cap-35-30/runs/…`, `~/Escritorio/RX550_Modo_Torneo_Backup_…`.
- Rutas en `MASTER-RESEARCH-STATUS.md` → 30+ citas a `experiments/FASE-*` (X).
- Rutas en `PROJECT-DOCUMENTATION-STATUS.md` → `experiments/…` para cada fase y `~/Escritorio/berchmark/instalados/`.
- `R2-GLOBAL-DOCUMENTATION-MAP.md` → mapa por archivo (todas las rutas del repo).
- `R2-HISTORICAL-EXPERIMENT-INVENTORY.md` → `rx550-power-sweep-20260918-…/` (en `~/`).
- `research_log.md` → `experiments/M1-…`, power-sweep.
- Manifiestos `FASE-R4B-GOVERNOR/results/v23/session1/fase{1,2}/`.

## 16. Decisiones pendientes (para el usuario)

1. **Autorizar** el mapeo completo de §13 (tabla ORIGEN→DESTINO).
2. **Docs de estado y conocimiento:** ¿`00-INDICE/` para estado/índices y `02-ARQUITECTURA/` para conocimiento (mi propuesta), u otra asignación?
3. **Master docs:** confirmar roles (fuente viva `MASTER-RESEARCH-STATUS`; plan `MASTER-PLAN`; resumen `FINAL-RESEARCH-STATUS`; índice ecosistema `PROJECT-DOCUMENTATION-STATUS`) sin merge ni borrado.
4. **NotebookLM:** aprobar conversión de las 50 copias a symlinks (mismos nombres, carpeta plana, ≤50) y autorizar la prueba del flujo de carga; si falla, definir alternativa.
5. **Power-sweep:** ¿mover la copia de home a `03-EXPERIMENTOS/` (evidencia integrada) dejando el backup como duplicado conservado, o dejar el backup como única fuente?
6. **Scripts legado:** confirmar CONSERVAR-EN-LUGAR + referencia desde `04-IMPLEMENTACION/`.
7. **FASE-R2:** ¿desglosar los FASE-E…Q-DESIGN hacia `04-IMPLEMENTACION/` o mantener la unidad R-2 en `01-AUDITORIA/`?
8. **FASE-R0:** ¿`05-FUENTES-EXTERNAS/` (propuesta) u `01-AUDITORIA/`?
9. **POLARIS12-MAP:** ¿`02-ARQUITECTURA/` (propuesta) u `03-EXPERIMENTOS/`?
10. **IMPLEMENTATION-READINESS:** audit → `01-AUDITORIA/` (confirmado); `IMPLEMENTATION-ROADMAP.md` y `IMPLEMENTATION-SAFETY-RULES.md` → propongo `04-IMPLEMENTACION/` (o junto al audit; elegir).
11. **Temporales `/tmp`:** ¿autorizar su eliminación (verificada ausencia de evidencia única)?
12. **git:** ¿inicializar un repositorio git en la nueva raíz antes de mover (trazabilidad/rollback)?
13. **`00-INDICE/FUENTES-FALTANTES.md`:** ¿crearlo durante la reorganización (con los UNKNOWNs ya documentados en `open_questions.md`/`R1-7-CRITICAL-GAPS.md`) o después?
14. **Exportaciones:** confirmar exclusión y registro (sin movimiento).
15. **Cantidad objetivo:** confirmar que `MAX-50` = los 50 actuales (sin cambios de selección) o revisar inclusiones/exclusiones de la curaduría.

---

## Salida A–G requerida por el encargo (resumen)

### A. Tabla de movimientos (resumen)
Ver §13. Resumen: 6 grupos a `01-AUDITORIA/`, 6 a `03-EXPERIMENTOS/`, 2 a `02-ARQUITECTURA/`, 3 a `04-IMPLEMENTACION/`, 2 a `05-FUENTES-EXTERNAS/`, 2 a `00-INDICE/`; ~8 elementos CONSERVAR-EN-LUGAR; 3 temporales propuestos a descarte; 50 NotebookLM NO-MOVER (conversión pendiente).

### B. Tabla NotebookLM
Ver §5 (50/50 mapeados; todos idénticos; todos propuestos MANTENER, con prefijo de nombre conservado).

### C. Scripts duplicados
Ver §6: 2 familias (modo torneo: `~/rx550-torneo` v1 y `~/bin/rx550-torneo` v2, ambos == backup; barrido: `.sh` == backup y `.bak` anterior). Herramienta operativa real = CLI Python del repo (235 B launcher). No son el mismo código.

### D. Evidencia única
Ver §4: `kalm_dataset_v2.csv`, `gpu_real_data.csv`, snapshot HW/Vulkan, `PHASE0-AUDIT-STATUS.md`, `shell-history-rx550-kalm.txt`, experimentos históricos mesa-e1/e2/e3/ab/resolution/p1/p2, datos `power-sweep-*` (contexto invalidación `power1_input`), SESIONES de PROYECTOS_LUCAS, y la capa verificada del repo (D-1/2, R-4*, M1, WORKLOAD-SINTETICO).

### E. Riesgos
Ver §14: no-git (sin rollback), ~30+ rutas citadas en docs maestros, manifiestos con rutas, launcher `PYTHONPATH` relativo, riesgo NotebookLM con symlinks, desglose R-2, duplicado power-sweep.

### F. Decisiones pendientes
Ver §16 (15 items).

### G. Resumen numérico
| Métrica | Valor |
|---|---|
| Documentos totales (repo) | 172 `.md` (+1 `.txt` spec) |
| Documentos duplicados | 50 (NotebookLM) + 2 dirs power-sweep (×2) + 1 `.run` + 3 scripts legados (con copia en backup) |
| Documentos únicos | ~170 `.md` del repo + evidencia única del backup (lista §4) |
| Archivos fuera de la raíz | 50 NB + 5 scripts + 2 dirs de datos (home) + 1 build (656M) + 1 backup (31.584 f) + 2 proyectos históricos personales + software `berchmark` + 8 exportes + 3 temporales |
| Fuentes externas | 1 inventario + 2 manifiestos + 1 descarga + 1 partial + 8 f R-0 + referencia GPUPerfAPI |
| Fuentes faltantes registradas | 0 (`FUENTES-FALTANTES.md` no existe; crearlo en la reorganización) |
| Notas de NotebookLM | 50 (copias → symlinks pendientes) |
| Temporales | 3 (2 con write-test, 1 vacío) |
| Builds | 2 (home `mesa-26.2.2-build` 656M; backup `mesa-source`) |
| Backups | 1 consolidado con SHA256SUMS + 1 sistema histórico personal |
| Movimientos propuestos | ~20 grupos (§13) |
| Elementos que permanecen fuera de la raíz | NotebookLM, backup histórico, PROYECTOS_LUCAS, scripts legado, build Mesa, `berchmark/`, exportes `.txt`, temporales |