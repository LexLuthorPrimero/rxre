# AUDITORÍA DOCUMENTAL POST-REPARACIÓN — RX550-INVESTIGACION

**Fecha**: 2026-09-23 · **Raíz auditada**: `/home/lucas/Escritorio/RX550-INVESTIGACION/`
**Modo**: READ-ONLY. No se modificó, movió, renombró ni borró ningún fichero existente. No se ejecutó ningún script del proyecto. No se tocó Mesa, RX550, governors, sysctl ni servicios. No se hizo commit.
**Único fichero creado por esta auditoría**: este informe.

> **SNAPSHOT HISTÓRICO (reconciliación 2026-09-24):** este informe conserva los hallazgos
> y conflictos anteriores a la reconciliación; no es fuente de estado actual. Prevalecen
> `MASTER-RESEARCH-STATUS.md`, Addenda D6 y los resultados canónicos.

---

## A. Estado estructural

| Métrica | Valor |
|---|---|
| Ficheros totales | 1.819 |
| Directorios | 418 |
| Enlaces simbólicos | **0** |
| Tamaño | 480 MB |
| Documentos Markdown | 188 |
| Rama git | `main` · 8 commits |

### A.1 Estructura objetivo

| Directorio requerido | Estado | `.md` |
|---|---|---:|
| `00-INDICE/` | presente | 20 |
| `01-AUDITORIA/` | presente | 37 |
| `02-ARQUITECTURA/` | presente | 11 |
| `03-EXPERIMENTOS/` | presente | 44 |
| `04-IMPLEMENTACION/` | presente | 65 |
| `05-FUENTES-EXTERNAS/` | presente | 10 |
| `README.md` (raíz) | presente | 1 |

**La estructura objetivo se cumple al 100%.** No hay directorios extra de primer nivel ni symlinks residuales.

### A.2 Integridad frente al manifiesto pre-movimiento (1.645 entradas, re-mapeadas al árbol actual)

| Resultado | Nº | % |
|---|---:|---:|
| OK (hash idéntico) | 1.597 | 97,1% |
| Modificados (hash distinto) | 33 | 2,0% |
| Reubicados (existen en otra ruta) | 15 | 0,9% |
| **Perdidos** | **0** | **0%** |

Los 15 reubicados son los diseños FASE-E…FASE-Q, `EXPERIMENT-PRIORITY-MATRIX.md` y `SYNTHETIC-WORKLOAD-DESIGN.md` (ahora en `04-IMPLEMENTACION/`) más `R2-GLOBAL-DOCUMENTATION-MAP.md` (ahora en `00-INDICE/`).

### A.3 Conteos históricos (no sustituyen al actual)

| Fuente | Conteo | Fecha |
|---|---:|---|
| `REORGANIZATION-AUDIT.md:15,26-35` | 172 `.md` / 1.256 ficheros | pre-movimiento |
| `POST-REORGANIZATION-REFERENCES-AUDIT.md:7-10` | 178 `.md` / 1.654 ficheros | post-reorg |
| `REGISTRO-DE-MOVIMIENTOS.md:4,13-20` | 1.651 ficheros movidos | 23-sep 06:40 |
| **Actual** | **188 `.md` / 1.819 ficheros** | 23-sep |

### A.4 Otros hallazgos estructurales

- **279 basenames duplicados**, todos artefactos de corridas (`stdout.txt` ×89, `telemetry.csv`, `epoch`, `.rtopid`, `CMakeCCompiler.cmake`…). No hay duplicación de rutas completas Set I ni de directorios de primer nivel (`uniq -d` vacío).
- **Basura de compilación**: 2 directorios `__pycache__` y 10 `.pyc` en `04-IMPLEMENTACION/rx550-torneo/`.
- **No existe ningún hipervínculo Markdown** del tipo `[texto](ruta)`. Todas las referencias son textuales (backticks, tablas, prosa), por lo que las reparaciones futuras son sustituciones exactas.

---

## B. Set I — reparación verificada

**Resultado: 15/15 referencias reparadas, 9 destinos únicos, los 9 existen.** Registro: `POST-REORGANIZATION-SET-I-REPAIR-RESULT.md:24-69`.

| ID | Fichero:línea | Destino actual | Verificación |
|---|---|---|---|
| R1 | `00-INDICE/MASTER-PLAN.md:793` | `04-IMPLEMENTACION/projects/BERRETA/BERRETA-DESIGN.md` | existe |
| R2 | `MASTER-PLAN.md:794` | `…/projects/GHOST/GHOST-CACHE-DESIGN.md` | existe |
| R3 | `MASTER-PLAN.md:795` | `…/projects/RX-COMPRESSION-ENGINE/RX-COMPRESSION-ENGINE-DESIGN.md` | existe |
| R4 | `MASTER-PLAN.md:796` | `…/projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` | existe |
| R5 | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md:47` | `04-IMPLEMENTACION/projects/` (raíz) | existe |
| R6 | `PROJECT-DOCUMENTATION-STATUS.md:51` | `…/BERRETA/BERRETA-DESIGN.md` | existe |
| R7 | `:52` | `…/GHOST/GHOST-CACHE-DESIGN.md` | existe |
| R8 | `:53` | `…/RX-COMPRESSION-ENGINE/…DESIGN.md` | **existe, pero abreviado con elipsis** |
| R9 | `:54` | `…/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` | existe |
| R10 | `01-AUDITORIA/FASE-R3-NOVELTY-AUDIT/FASE-R3-FINAL-REPORT.md:119` | `04-IMPLEMENTACION/projects/` (Opción A) | existe, **no es mapeo 1:1** |
| R11 | `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md:43` | `…/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md` | existe |
| R12 | `TEST-TERMICO-READONLY.md:45` | `…/CLOSED-LOOP-QUALITY-GOVERNOR/POLARIS12-FEASIBILITY.md` | existe |
| R13 | `FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md:12` | `…/JITTER-REPROJECTION/EXPERIMENT-DESIGN.md` | existe |
| R14 | `PRECHECK-REPORT.md:13` | `…/JITTER-REPROJECTION/PRIOR-ART.md` | existe |
| R15 | `PRECHECK-REPORT.md:14` | `…/BERRETA/BERRETA-DESIGN.md` | existe |

**Verificaciones exigidas:**

| Comprobación | Resultado |
|---|---|
| Cada referencia apunta a un destino real existente | ✅ 15/15 (R8 inferido por elipsis) |
| No quedan referencias antiguas (las 15 cadenas exactas) | ✅ 0 apariciones |
| No hay rutas duplicadas en Set I | ✅ |
| No hay referencias ambiguas | ⚠️ R8 abreviada; R10 raíz vs. etiquetas I-01…I-10 |
| Contenido coherente con la nueva ubicación | ✅ |
| Referencias circulares | ⚠️ no hay ciclos de inclusión ni de filesystem; sí **ciclos textuales de navegación** (4 documentados: Repair-Result↔Registro, MASTER-PLAN↔MASTER-RESEARCH-STATUS, R2-MAP↔PROJECT-DOC-STATUS, R2-MAP↔MASTERS) |

**Salvedades Set I:**
1. **R8** no es un locator literal: `…/RX-COMPRESSION-ENGINE/…DESIGN.md` no resuelve con `test -e`.
2. **R10** apunta a la raíz de `projects/`; las etiquetas I-01…I-10 son internas, no nombres de directorio. La Opción A es válida para navegación, no como mapeo inequívoco.
3. `GHOST` y `GHOST-PREDICTIVE-CACHE` coexisten como directorios distintos (R2/R7 → `GHOST`; I-06 → `GHOST-PREDICTIVE-CACHE`). Nombres potencialmente confusos, no duplicados.
4. Fuera de la lista exacta quedan 2 residuos deliberados: `MASTER-PLAN.md:781` (U5) y `PRECHECK-REPORT.md:58` (metanota).

---

## C. Set H — PROTEGIDO, NO MODIFICADO

**Inventario: 10 ficheros** (8 con ruta absoluta operativa antigua + 2 con comentario ilustrativo). Discrepancia documental: `POST-REORGANIZATION-REFERENCES-AUDIT.md:362` dice **9**; el plan (`:258-259`) y el resultado (`:142-155`) dicen **10**. **El recuento operativo válido es 10.**

| ID | Ruta | Tipo | SHA256 actual vs documentado | MD5 actual (baseline nuevo) |
|---|---|---|---|---|
| H1 | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/telemetria.sh` | operativa | **COINCIDE** `20102c31…` | `14824e5e6b895840deecaa6e11608f13` |
| H2 | `…/FASE-D-COUNTERS-AUDIT/runs/etapa2/analizar_etapa2.py` | operativa | **COINCIDE** `b76c531e…` | `754fa90c2b266021d9b8e8a813e20d55` |
| H3 | `…/etapa2/auditoria_reconstruccion.py` | operativa | **COINCIDE** `5574b676…` | `631748027927ab3f002d9dbc7a475e2e` |
| H4 | `…/etapa2/orquestador.sh` | operativa | **COINCIDE** `8026df22…` | `b512cef35e802cd0ae8ef60debf44786` |
| H5 | `…/FASE-R4B-GOVERNOR/telemetry/telemetria.sh` | operativa | **COINCIDE** `922c429b…` | `e1e9dd0b3d74f401ff5a7532ca338ef3` |
| H6 | `…/FASE-R4B-THERMAL-TEST/run_thermal_replicate.sh` | comentario | **COINCIDE** `89331876…` | `7ed392af2452bfb8ef99e7cb7e2c898d` |
| H7 | `…/FASE-R4C-JITTER-OBSERVABILITY/harness/run_all.sh` | comentario | **COINCIDE** `d0e94ef5…` | `d6c89367a96a4309f1a3ff5a694ec7ef` |
| H8 | `…/R-14-SUPERPOSITION-DISSECTION/run_superposition.sh` | operativa | **COINCIDE** `0ed5f34f…` | `1ed55f9e866df679a7c0072127c5f912` |
| H9 | `…/ep06-soak-cap-20260919-205645/soak-final.sh` | operativa | **COINCIDE** `8d666328…` | `8265d324489bb4a95e2889951f951922` |
| H10 | `…/ep06-soak-cap-20260919-205645/soak-probe.sh` | operativa | **COINCIDE** `4d6a12b8…` | `9c4401921d0589eb5a2611120771d366` |

**Conclusión de integridad: Set H está intacto bit a bit (10/10 SHA256 coinciden).** Los mtimes van del 19 al 22 de septiembre, **todos anteriores** a la reorganización (23-sep 06:24). No existía baseline MD5 previo, por lo que el MD5 actual se registra por primera vez como referencia futura (no es comparable con los SHA256).

**Set H NO es reejecutable en el estado actual** (NO-GO) por rutas y dependencias rotas:

| Dependencia rota | Efecto |
|---|---|
| `/home/lucas/Escritorio/RX550_Iterative_Research/experiments/` existe pero **vacío** | H1–H5, H8–H10 apuntan a hojas inexistentes |
| `/tmp/opencode/ep06_base.txt` ausente | H9 y H10 no pueden arrancar |
| `/dev/dri/renderD129` ausente | H10 no puede abrir el nodo DRM |
| `$H` usado sin declarar en `soak-probe.sh:10` | fallo de expansión |
| `soak-final.sh:8,13` escribe `power1_cap` vía `sudo tee` | **no es un script read-only** |

Referencias externas confirmadas existentes: `…/berchmark/instalados/Unigine_Superposition-1.1/bin/superposition`, `/usr/share/vulkan/icd.d/{radeon,lvp}_icd.x86_64.json`, `/usr/bin/{radeontop,umr,glmark2,vkmark}`, `/sys/class/drm/card1/device/hwmon/hwmon2`.

---

## D. Referencias globales — clasificación A/B/C/D/E/F

| Clase | Nº aprox. | Criterio |
|---|---:|---|
| **A** válida actual | 9 grupos | destino canónico existente |
| **B** histórica a conservar | 2 | raíz antigua conservada, no operativa |
| **C** rota reparable | 12 | destino concreto inexistente |
| **D** ambigua | ~30 | abreviada, conceptual, wildcard, externa o contextual |
| **E** futura | 8 grupos | documento/salida aún no generada |
| **F** no tocar | 10 Set H + artefactos congelados | backups, auditorías, logs, manifiestos, CMake generado, NotebookLM |

**B — Raíces históricas conservadas:** `/home/lucas/Escritorio/RX550_Iterative_Research/` (existe, solo con `experiments/` vacío), `/home/lucas/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/`, `/home/lucas/Escritorio/berchmark/instalados/`, `/home/lucas/Escritorio/PROYECTOS_LUCAS/`, `/opt/mesa-26.2.2-rx550-haswell`, `/home/lucas/.local/state/rx550-torneo/` — **todas existen**.

**F — No tocar highlights:** los 10 scripts de Set H; `m1-schedule.json` (rutas `run_dir` antiguas); artefactos CMake/Ninja generados (`CMakeCache.txt`, `build.ninja`, `.ninja_deps`, `CMakeConfigureLog.yaml`); `state_*.txt` (los `lrwxrwxrwx` son **texto** de snapshot, no enlaces físicos); los 6 documentos de auditoría/reparación; `REORGANIZACION-MANIFEST.sha256`; las 50 copias de NotebookLM.

---

## E. Documentos centrales

| Documento | Estado | Problema |
|---|---|---|
| `README.md` (raíz) | **obsoleto** | `:21-29` presenta la reorganización y las reparaciones como **pendientes**, cuando `REGISTRO-DE-MOVIMIENTOS.md:3-5` las registra como ejecutadas |
| `00-INDICE/README.md` | **legado ambiguo** | `:8,24-31` cita `experiments/fase-a…`, `experiments/fase-b…`, `experiments/ep05…`, `experiments/ep06…`, `experiments/M1…` y `RX550_BUILD_SPECIFICATION.txt` en `00-INDICE` (hoy en `02-ARQUITECTURA/`). No declara si es índice vivo o snapshot |
| `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` | **mixto/desactualizado** | `:23,44` declara la raíz antigua y una capa `experiments/`; se autodeclara «mapa de navegación para un investigador nuevo» (`:10-15`). Decisión U2 pendiente |
| `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md` | **contradictorio** | `:195,197` usa `experiments/EXPLORATORIO-GravityMark/runs/…`; y `:62-72,184-197` afirma 4 instaladores y ejecuciones, frente a `README.md:3,7-24` y `SOURCES-AND-EXECUTION.md:5-10,23-27` que dicen que solo se descargó GravityMark y Superposition fue cancelado |
| `01-AUDITORIA/FASE-R1…/R1-5-DOCUMENTATION-STATUS.md` | **aliases obsoletos** | `:60-63` cita `R0-2-MCLK-POLARIS-MEMORY.md`, `R0-3-MESA-GFX8-WORKAROUNDS.md`, `R0-4-LEXA-POLARIS12-SPECS.md`, `R0-5-RX550-EXTERNAL-BENCHMARKS.md`; los nombres actuales en `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/` son distintos |
| `FUENTES-FALTANTES.md` | **INEXISTENTE** | citado en `README.md:28`, `REORGANIZATION-AUDIT.md:156,260,294` |
| `IMPLEMENTATION-ROADMAP.md` | **INEXISTENTE** | citado en `IMPLEMENTATION-READINESS-AUDIT.md:927-928` |
| `IMPLEMENTATION-SAFETY-RULES.md` | **INEXISTENTE** | citado en `IMPLEMENTATION-READINESS-AUDIT.md:927-928` |
| `PROJECT-ROADMAP.md` | **INEXISTENTE** | citado en `MASTER-PLAN.md:5` (norte conceptual) |

**Huecos de indexación de primer nivel** (existen pero no están en las tablas del maestro): las 4 auditorías de background (`AUDITORIA-CONSUMO-SEGUNDO-PLANO.md`, `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md`, `AUDITORIA-ACTUALIZACIONES-AUTOMATICAS.md`, `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md`), `IMPLEMENTATION-READINESS-AUDIT.md` y los 3 documentos v2.3 de R-4B (`AUDITORIA-PRE-RUN-v2.3.md`, `EXP-F4-A-PROTOCOL-v2.3.md`, `EXP-F4-A-RESULTADOS-v2.3.md`).

**Estados declarados normalizados** (del agente + verificación): `COMPLETADA` (fases A,B,C,D1-2, EP-05/06, M1, R0,R1,R2,R3,R3.1,R4A,R4C) · `PARADA` (S2-v2.3, rc=9) · `INCONCLUSIVE` (veredicto global R4B) · `PENDING` (FASE E–J) · `PLANIFICADA` (K–Q) · `NO AUTORIZADO` (escrituras, contadores, Mesa, PowerPlay) · `UNKNOWN` (bandwidth PCIe real, GDDR5, GTT) · `NO REPRODUCIBLE` (régimen 17/09).

---

## F. Trazabilidad (HIPÓTESIS → EXPERIMENTO → EVIDENCIA → RESULTADO → LIMITACIÓN → CONCLUSIÓN → ESTADO)

| Conclusión | Cadena | Diagnóstico |
|---|---|---|
| M1 no discrimina cap 35/30 | **C** completa | ✅ |
| Synthetic workload = fetch-latency/autopacing | **C** completa | ✅ |
| R-4C jitter observable | **C** completa | ✅ (dentro del alcance host-visible/RADV/lavapipe) |
| Mesa CUSTOM no causa E5 | **P** parcial | limitada a 3 escenas y arranque frío |
| FASE D: diferencia Superposition/E-03 | **P** parcial | API/workload confundidos; H1/H4 solo direccionales |
| E1/E3 no reproducibles | **P** parcial | runner E1 ausente |
| R-4A bandwidth real | **P** parcial | PCIe sí; bandwidth real no medido ni preservado |
| R-4B governor reduce p99 | **P** parcial | S2 incompleta; evidencia de interferencia no en disco |
| R-14: ALU/geometría causa el techo | **R** rota | la conclusión causal excede la telemetría; FASE D solo apoya dirección |
| IDs GFX8 de GPUPerfAPI | **D** documental | verificación documental, no ejecución de contador |
| Capacidades del mapa Polaris12 | **D/P** | claims locales y teóricas mezcladas |
| Power sweeps 132309/140527 | **R** rota | sin informe, método, estado ni cadena |

**Saltos de inferencia detectados (NO se corrigen aquí):**

1. **“Potencia real” vs estimador SMU**: el proyecto reconoce que `power1_input` es un estimador SMU (`WORKLOAD-SINTETICO/RESEARCH.md:93-102`, `AUDIT-001/ERRATA.md:34-49`), pero `FINAL-RESEARCH-STATUS.md:7-9`, EP-06 y `EVIDENCE-MATRIX.md:50-51` speak de “draw real”. Sin vatímetro independiente, la formulación segura es “potencia estimada por sensor SMU”.
2. **R-14 interpreta correlación como causalidad** (`:94-105,121-132` afirma “SÍ ALU/compute”), mientras FASE D es prudente (H1/H4 solo `APOYADA` direccionalmente).
3. **R-4B depende de evidencia no preservada**: la PARADA D se atribuye a interferencia externa, pero `/tmp/opencode/micro12/vkmark30-telemetry.csv` y `/tmp/opencode/marcar_ventanas.py` ya no existen → “causa probable documentada”, no verificada.
4. **POLARIS12-MAP vs R-4A**: `POLARIS12-MAP.md:183,230` presenta PCIe Gen3×8 como verificado/negociado; R-4A verificó **Gen2×4** (root port limitado). `POLARIS12-MAP.md:84,232` presenta 2 ACE como VERIFICADO sin lectura local. Debe separarse capacidad máxima / negociada / documentada / verificada.
5. **R-4C no demuestra observabilidad arbitraria**: prueba push constants, UBO host-visible, RADV y lavapipe; **no** DEVICE_LOCAL, ni ANV, ni motores fuera del harness.

---

## G. Experimentos

**16 directorios de primer nivel; 13 con informe `.md`; 3 sin informe:**

| Sin informe `.md` | Observación |
|---|---|
| `rx550-power-sweep-20260918-132309/` | 194 ficheros; los `.txt` muestran **Intel/Vulkan**, no AMD → sweep inservible para RX550 |
| `rx550-power-sweep-20260918-140527/` | 194 ficheros; datos AMD, pero los `results.csv` tienen **cabeceras desalineadas** (`sclk_avg=0.0` con valores que parecen MCLK/temp) |
| `results/` | solo `results/logs/session1.log` con `BUILD FAILED` |

**Completitud de campos** (ID/O/M/F/HW/R/E/X/L/S): mejores = `WORKLOAD-SINTETICO`, R-4C, EP-05, EP-06, M1. Huecos = FASE A (sin objetivo/metodología/limitaciones/estado), FASE B (sin rutas de evidencia ni estado), R-4A (sin captura raw preservada), los 2 power sweeps y `results/`.

**Búsqueda literal de estados:** `INCONCLUSIVE` 8 líneas (todas R-4B) · `UNKNOWN` 34 en experimentos + 21 en índices · `COMPLETE` 3 (todas prechecks, no cierres) · `TODO` 4 (**falsos positivos**: “todo lo no verificado”) · `PENDING`/`ABORTED`/`SUPERSEDED`/`UNSUPPORTED`/`FAILED`/`DRAFT` = **0 apariciones**. El proyecto usa español (`PENDIENTE`, `INCONCLUSO`, `PARADA D`, `DESCONOCIDO`) → el recuento literal no es métrica de estado.

**Desfase crítico de estado (P0):** `MASTER-RESEARCH-STATUS.md:3,278-337,387,406-424` afirma que v2.3 es propuesta no ejecutada y S2 no iniciada; `EXP-F4-A-RESULTADOS-v2.3.md:3-5,11-32,152-166` documenta S1-v2.3 completa, S2 `PARADA D` (rc=9), muestra incompleta, R1–R6 no evaluables, R7 `INCONCLUSIVE` y veredicto global **`INCONCLUSO`**. Además `EXP-F4-A-PROTOCOL-v2.3.md:3-4` (“ninguna trial ejecutada”) contradice `:224-230` (S1/S2 autorizadas), y el informe heredado `EXP-F4-A-RESULTADOS.md:11-15,27-40` conserva `TBD` y cita `results/session2/` **inexistente**.

**Predicción térmica disputada:** `RESULTADOS-MINITEST-7.3-B.md:100-115` extrapola `t90≈221 s`; `AUDITORIA-PRE-RUN-v2.3.md:51-76` muestra `t90` real de 171,9 s (REP1) y 134,8 s (REP2) por no linealidad. No debe presentarse como hecho operativo.

**Evidencia declarada y ausente:** `/tmp/opencode/{micro12/vkmark30-telemetry.csv, marcar_ventanas.py, analyze_minitest_ramp.py, audit_p2_thermal.py, audit_power_win.py, run_variant.sh, fakehome/.drirc, rt_idle.csv, gpa311/}`, `…/FASE-R4B-GOVERNOR/results/session2/`, `…/v23/session2/fase1/manifest.json`, `…/v23/session2/fase2/metrics.json`, `**/verdict.json`, `EXPLORATORIO-GravityMark/runs/200k/{times,stats}_200k.txt` (esta última ausencia justificada por timeout documentado).

---

## H. NotebookLM

| Comprobación | Resultado |
|---|---|
| Ruta | `/home/lucas/Escritorio/RX550-INVESTIGACION-NOTEBOOKLM/` |
| Existe | ✅ (dir regular, mtime 23-sep 03:59) |
| Entradas | **50 ficheros, 0 directorios** |
| **Symlinks reales** | **0** — son **copias regulares**, no enlaces |
| Symlinks rotos | 0 (no hay symlinks) |
| Duplicados por hash | **0 grupos** |
| Colisión de nombres con el repo | **ninguna** (llevan prefijo `01-`, `02-`…) |
| Antigüedad | 23-sep 03:44 → **snapshot anterior** a la reorganización (06:24) |

**Conclusión:** NotebookLM es una **copia plana de 50 documentos**, no un conjunto de enlaces. No hay destinos que reparar ni documentos que “deberían existir”. Debe tratarse como **F (no tocar)** y marcarse como snapshot si se mantiene.

---

## I. Git

| Dato | Valor |
|---|---|
| Rama | `main` |
| HEAD | `c6146788e0d4fb12d9b0ec1209fa2840692de0c5` |
| Último commit | `c614678` — 2026-09-23 06:40:59 — *“Registro de movimientos completado + verificación global de integridad (1651 archivos)”* |
| Commits totales | 8 |
| Modificados (`M`) | **36** |
| Untracked (`??`) | **10** |
| Otros | 0 |

**Modificados (36):** 6 en `00-INDICE`, 8 en `01-AUDITORIA`, 2 en `02-ARQUITECTURA`, 10 en `03-EXPERIMENTOS`, 6 en `04-IMPLEMENTACION`, 2 en `05-FUENTES-EXTERNAS`, más `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/{FASE-R0-…FINAL-REPORT,R0-2-POWERPLAY-MCLK-SMU7}.md`.

**Untracked (10):** `AUDITORIA-ACTUALIZACIONES-AUTOMATICAS.md`, `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md`, `AUDITORIA-CONSUMO-SEGUNDO-PLANO.md`, `POST-REORGANIZATION-REFERENCE-REPAIR-PLAN.md`, `POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md`, `POST-REORGANIZATION-REFERENCES-AUDIT.md`, `POST-REORGANIZATION-SET-I-AUDIT.md`, `POST-REORGANIZATION-SET-I-REPAIR-RESULT.md`, `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md`, `REGISTRO-DE-REPARACION-REFERENCIAS.md`.

**Inconsistencia detectada:** 3 ficheros que git marca modificados tienen contenido **idéntico al manifiesto pre-movimiento** (`04-IMPLEMENTACION/FASE-E-REAL-GAME-BASELINE-DESIGN.md`, `FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md`, `SYNTHETIC-WORKLOAD-DESIGN.md`). Su modificación actual **revierte o ignora** lo que el commit `c614678` registró. Requiere decisión humana.

---

## J. Referencias rotas (C) — 12

| # | Fichero:línea | Referencia rota | Destino real |
|---|---|---|---|
| C1 | `00-INDICE/README.md:25-29` | `experiments/fase-a-discriminacion-20260919-114241/` | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/` |
| C2 | ídem | `experiments/fase-b-cap-probe-20260919-122038/` | `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/` |
| C3 | ídem | `experiments/ep06-soak-cap-20260919-205645/` | `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/` |
| C4 | ídem | `experiments/ep05-mesa-custom-20260919-212249/` | `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249/` |
| C5 | ídem | `experiments/M1-cap-35-30/` | `03-EXPERIMENTOS/M1-cap-35-30/` |
| C6 | `03-EXPERIMENTOS/M1-cap-35-30/run-m1.sh:6,10,13,16` | `$HERE/../../rx550-torneo` → resuelve a `<raíz>/rx550-torneo` (inexistente) | `04-IMPLEMENTACION/rx550-torneo/` |
| C7 | `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md:195` | `experiments/EXPLORATORIO-GravityMark/runs/RESULTADO-Superposition.md` | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/…` |
| C8 | `BENCHMARK-INVENTORY.md:197` | `experiments/EXPLORATORIO-GravityMark/runs/RESULTADO.md` | ídem |
| C9 | `04-IMPLEMENTACION/FASE-G-MEMORY-VRAM-GTT-DESIGN.md:7` | `projects/GHOST/GHOST-CACHE-DESIGN.md` (sin `04-IMPLEMENTACION/`) | `04-IMPLEMENTACION/projects/GHOST/…` |
| C10 | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/PRIOR-ART.md:99` | `projects/JITTER-REPROJECTION/PRIOR-ART.md` | `04-IMPLEMENTACION/projects/JITTER-REPROJECTION/PRIOR-ART.md` |
| C11 | `01-AUDITORIA/FASE-R2…/R2-HISTORICAL-EXPERIMENT-INVENTORY.md:54` | `/home/lucas/RX550_Modo_Torneo_Backup_2026-09-19_0836/experiments/` (falta `/Escritorio`) | `/home/lucas/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/` |
| C12 | `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/driver.sh:3` y `ep05…/scripts/{ab-e5.sh,ab-e5-vk.sh,env-check.sh}:3` | `/tmp/opencode/{fase_b_base,ep05_base}.txt` (volátiles) | requiere decisión: reubicar o marcar como histórico |

---

## K. Referencias ambiguas (D) — selección

| Fichero:línea | Ambigüedad |
|---|---|
| `MASTER-RESEARCH-STATUS.md:371` | `rx550-torneo/` sin `04-IMPLEMENTACION/` |
| `MASTER-PLAN.md:781` | `experiments/ A–D/R-0/R-1/sintético` (U5, excluido del Set I) |
| `PROJECT-DOCUMENTATION-STATUS.md:3,25,27-45,60,64` | “raíz del repositorio”, `fase-b…`, `ep05…`, `rx550-torneo/README-*.md` |
| `R2-GLOBAL-DOCUMENTATION-MAP.md:23,44,50-175` | mapa pre-movimiento completo (decisión U2 pendiente) |
| `MASTER-PLAN.md:82,104`, `MASTER-RESEARCH-STATUS.md:50,388`, `PROJECT-DOCUMENTATION-STATUS.md:61` | `~/Escritorio/berchmark/instalados/` (externo deliberado, existe) |
| `BENCHMARK-INVENTORY.md:3,27,120,186,190-202` | rutas externas de benchmarks y `/opt/mesa-26.2.2-rx550-haswell` |
| `RESULTADOS-MINITEST-7.3-B.md:163`, `EXP-F4-A-MINITEST-RAMP-GOV-PLAN.md:107` | `/tmp/opencode/analyze_minitest_ramp.py` no archivado |
| `EXP-F4-A-RESULTADOS-v2.3.md:18,165-166` | loggers/analizadores bajo `/tmp/opencode/` |
| `FASE-D-ETAPA-3-PRECHECK.md:32,239` | `/tmp/opencode/rt_idle.csv` |
| 11 cabeceras de `04-IMPLEMENTACION/projects/*/README.md` y 4 `*-DESIGN.md` | prefijo `projects/...` sin el directorio superior |
| `IMPLEMENTATION-READINESS-AUDIT.md` (múltiples) | localizadores abreviados y temporales; auditoría congelada (F) |
| Placeholders | `R1-1..R1-15`, `F2-*`, `projects/I-*`, rutas con `…`, `FUSION-01..07` → notación de conjunto, no destinos literales |

---

## L. Documentos faltantes

| Documento | Citado en | Tipo |
|---|---|---|
| `00-INDICE/FUENTES-FALTANTES.md` | `README.md:28`, `REORGANIZATION-AUDIT.md:156,260,294` | tarea diferida explícita |
| `01-AUDITORIA/IMPLEMENTATION-READINESS/IMPLEMENTATION-ROADMAP.md` | `IMPLEMENTATION-READINESS-AUDIT.md:927-928` | pendiente |
| `01-AUDITORIA/IMPLEMENTATION-READINESS/IMPLEMENTATION-SAFETY-RULES.md` | `IMPLEMENTATION-READINESS-AUDIT.md:927-928` | pendiente |
| `PROJECT-ROADMAP.md` | `MASTER-PLAN.md:5` | norte conceptual, no archivo |
| Informes `.md` para los 2 power sweeps | — | nunca se redactaron |
| `results/session1/fase1/`, `fase2/` con contenido | referenciado por el layout heredado | dirs vacíos |

**Entregables R1 no materializados** (no son ficheros faltantes sino tareas de rango `R1-1..R1-15`): `R1-2`, `R1-3`, `R1-4`, `R1-11`, `R1-12`, `R1-14` no tienen fichero ni mención textual.

---

## M. Contradicciones

| # | Contradicción | Lado A | Lado B |
|---|---|---|---|
| M1 | **Estado R-4B** | `MASTER-RESEARCH-STATUS.md:3,278-337` → v2.3 no ejecutada, S2 no iniciada | `EXP-F4-A-RESULTADOS-v2.3.md:11-32,152-166` → S1 completa, S2 `PARADA D`, veredicto `INCONCLUSO` |
| M2 | **Protocolo v2.3 consigo mismo** | `EXP-F4-A-PROTOCOL-v2.3.md:3-4` → ninguna trial ejecutada | ídem `:224-230` → S1/S2 autorizadas |
| M3 | **Temperatura DIST** | `RESULTADOS-MINITEST-7.3-B.md:100-115` → `t90≈221 s` | `AUDITORIA-PRE-RUN-v2.3.md:51-76` → `t90` real 171,9/134,8 s |
| M4 | **PCIe** | `POLARIS12-MAP.md:183,230` → Gen3×8 verificado | R-4A (`MASTER-RESEARCH-STATUS.md:237-243`) → Gen2×4 |
| M5 | **Bandwidth VRAM** | `FASE-G-MEMORY-VRAM-GTT-DESIGN.md:42,91` → 501 GB/s | R-4A estima 96–112 GB/s |
| M6 | **Benchmarks** | `BENCHMARK-INVENTORY.md:62-72,184-197` → 4 instalados y ejecutados | `RX550_Benchmarks/README.md:3,7-24` y `SOURCES-AND-EXECUTION.md:5-10,23-27` → solo GravityMark descargado, Superposition cancelado |
| M7 | **Superposition** | `BENCHMARK-INVENTORY.md` lo mantiene como candidato prioritario | el mismo doc lo marca descartado por licencia/config |
| M8 | **README raíz** | `README.md:21-29` → reorganización pendiente | `REGISTRO-DE-MOVIMIENTOS.md:3-5` → ejecutada y verificada |
| M9 | **Conteo Set H** | `POST-REORGANIZATION-REFERENCES-AUDIT.md:362` → 9 ficheros | plan `:258-259` y resultado `:142-155` → 10 |
| M10 | **Manifest R-4B** | `results/v23/session1/fase1/manifest.json:3-5` → `"version": "2.1"`, `T_ms=9.153` | `EXP-F4-A-PROTOCOL-v2.3.md:39-45` → `T=9.168 ms` (Δ 0,16%, explicado en `:130-135`) |
| M11 | **Git vs manifiesto** | 3 ficheros `M` con hash idéntico al pre-movimiento | el commit `c614678` registró otro contenido |

---

## N. Reparaciones recomendadas (NO ejecutadas, requieren autorización)

1. **P0 — Actualizar el estado vivo de R-4B** en `MASTER-RESEARCH-STATUS.md` (S1-v2.3 completa, S2 `PARADA D`, muestra incompleta, veredicto `INCONCLUSO`) mediante addenda fechada que conserve el texto anterior como historial.
2. **P0 — Marcar el estado canónico**: `EXP-F4-A-RESULTADOS-v2.3.md` es el vigente; `EXP-F4-A-RESULTADOS.md` (heredado, con `TBD`) y las secciones obsoletas del protocolo deben marcarse como históricos.
3. **P0 — Recuperar o reconocer la evidencia perdida de `/tmp/opencode/`** de R-4B; si no es recuperable, declarar la PARADA D como “causa probable no verificable”.
4. **P1 — Reparar C1–C5** (`00-INDICE/README.md:25-29`) y **C11** (typo `/Escritorio`).
5. **P1 — Reparar C6** (`run-m1.sh` → `04-IMPLEMENTACION/rx550-torneo`) solo si el script vuelve a ser ejecutable; si no, marcarlo histórico.
6. **P1 — Reparar C7–C10** (`BENCHMARK-INVENTORY.md:195,197`, `FASE-G:7`, `PRIOR-ART.md:99`).
7. **P1 — Reconciliar M3, M4, M5, M6/M7** con lenguaje prudente.
8. **P1 — Sustituir “draw real” por “potencia estimada por sensor SMU”** en los documentos citados.
9. **P1 — Armonizar R-14 con FASE D**: “correlaciona con mayor actividad direccional; la causalidad no está aislada”.
10. **P2 — Normalizar vocabulario de estados** (tabla de equivalencias ES/EN).
11. **P2 — Completar campos** de FASE A, FASE B y R-4A; redactar informes para los 2 power sweeps o marcarlos no utilizables.
12. **P2 — Redactar o registrar** los 3 documentos diferidos y añadir sección de índice para auditorías de background/readiness.
13. **P2 — Limpiar artefactos** `__pycache__`/`.pyc` (tras confirmar que no están referenciados).
14. **NO tocar Set H** sin autorización específica, y su reparación debe ser estática, sin ejecutar los scripts.

---

## O. Riesgos

| Riesgo | Nivel | Mitigación |
|---|---|---|
| Corregir Set H y romper la reproducibilidad histórica de 10 scripts | **Alto** | Set H es F; cualquier cambio requiere autorización propia y copia previa |
| “Reparar” rutas de artefactos congelados (CMake, JSON, logs) y romper la trazabilidad de corridas | **Alto** | Clase F; solo regenerar, nunca editar |
| Promover R-4B de `INCONCLUSO` a `SUPPORTED` | **Alto** | Evidencia n=1..3 no autoriza veredicto; requiere A/B controlado |
| Tomar `t90≈221 s` o PCIe Gen3×8 como hechos | **Medio** | Marcar como extrapolación/documental |
| Confundir `power1_input` con vatímetro | **Medio** | Lenguaje explícito de estimador |
| Perder los 36 `M` + 10 `??` sin commit | **Medio** | Ninguna escritura hasta revisión; este informe es el único fichero nuevo |
| Convertir NotebookLM en enlaces y romper la copia de 50 documentos | **Bajo** | Se documenta como copia plana (H) |
| Que la auditoría itself se mezcle con el estado científico del proyecto | **Bajo** | Este informe solo documenta; el hallazgo del logger (§7) es metodológico |

---

## 7-bis. Hallazgo metodológico del logger HDD 2026-09-23 (NO es evidencia de RX550)

Durante la investigación de consumo en segundo plano se detectaron **9 juegos de colectores huérfanos** que continuaron escribiendo logs al HDD tras finalizar cada captura.

- **Causa**: el `kill` del script terminaba el subshell; los hijos `mpstat`/`vmstat`/`iostat` quedaban vivos y seguían anexando cada 1–10 s.
- **Efecto**: contaminación de los ficheros de captura (p. ej. `autoONv4_mpstat1s.txt` llegó a 19.131 líneas de las que solo 12.001 eran de la ventana) y de las métricas de disco.
- **Resolución**: huérfanos terminados; **todos los análisis re-filtrados por timestamp**; logger v5 corregido con `timeout` para auto-terminarse, y **verificado que no deja residuos**.
- **Bug adicional**: con decimales de coma (`8,88`) awk realizaba comparación de cadenas, por lo que un informe previo declaró un máximo de iowait de **9,00%** cuando el valor real era **50,73%**; recalculado en Python.

**Esto es evidencia metodológica del sistema de medición y NO evidencia de rendimiento de la RX550.** No debe citarse en ningún documento de resultados de GPU.

---

# LISTAS FINALES

## 1. Archivos que necesitan reparación (14)

| # | Fichero | Motivo |
|---|---|---|
| 1 | `00-INDICE/README.md` | C1–C5 + rol índice/snapshot sin declarar |
| 2 | `00-INDICE/MASTER-RESEARCH-STATUS.md` | M1 (estado R-4B obsoleto), K1 |
| 3 | `00-INDICE/README.md` (raíz) | M8 (narrativa obsoleta) |
| 4 | `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` | U2 pendiente, K2 |
| 5 | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | K3 (localizadores abreviados) |
| 6 | `00-INDICE/FINAL-RESEARCH-STATUS.md` | “draw real” vs estimador SMU |
| 7 | `01-AUDITORIA/FASE-R1…/R1-5-DOCUMENTATION-STATUS.md` | aliases R0 inexistentes |
| 8 | `01-AUDITORIA/FASE-R2…/R2-HISTORICAL-EXPERIMENT-INVENTORY.md` | C11 (typo) |
| 9 | `03-EXPERIMENTOS/M1-cap-35-30/run-m1.sh` | C6 (ruta relativa rota) |
| 10 | `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/driver.sh` | C12 (`/tmp` volátil) |
| 11 | `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249/scripts/{ab-e5.sh,ab-e5-vk.sh,env-check.sh}` | C12 (`/tmp` volátil) |
| 12 | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md` | M3/M10 (redondeo `t90`, versión de manifiesto) |
| 13 | `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/RESULTADOS-MINITEST-7.3-B.md` | M3 (extrapolación no lineal) |
| 14 | `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md` | C7, C8, M6, M7 |

## 2. Referencias que necesitan reparación (12 + ~30 ambiguas + 8 futuras)

- **Concretas rotas (C)**: las 12 de la sección J.
- **Ambiguas (D)**: ~30, de las cuales 12 cabeceras de `04-IMPLEMENTACION/projects/*` con prefijo `projects/…`, 1 en `MASTER-RESEARCH-STATUS.md:371`, y las de `R2-GLOBAL-DOCUMENTATION-MAP.md`.
- **Futuras (E)**: `FUENTES-FALTANTES.md`, `IMPLEMENTATION-ROADMAP.md`, `IMPLEMENTATION-SAFETY-RULES.md`, `PROJECT-ROADMAP.md`, `snapshot-gfx800-PRECHECK.txt`, `snapshot-gmc810-PRECHECK.txt`.
- **Volátiles a reubicar o marcar históricas**: las 12 rutas bajo `/tmp/opencode/` citadas en R-4B, R-4C, FASE D y thermal.

## 3. Documentos que necesitan creación (8)

1. `00-INDICE/FUENTES-FALTANTES.md`
2. `01-AUDITORIA/IMPLEMENTATION-READINESS/IMPLEMENTATION-ROADMAP.md`
3. `01-AUDITORIA/IMPLEMENTATION-READINESS/IMPLEMENTATION-SAFETY-RULES.md`
4. Informe de `rx550-power-sweep-20260918-132309` (o nota de “no utilizable”)
5. Informe de `rx550-power-sweep-20260918-140527` (o nota de “no utilizable”)
6. Nota de estado para `03-EXPERIMENTOS/results/` (`BUILD FAILED`)
7. Sección de índice para auditorías de background y readiness
8. Tabla de normalización de estados ES/EN

## 4. Documentos que necesitan actualización (6)

`MASTER-RESEARCH-STATUS.md` (M1) · `MASTER-PLAN.md` (U5, benchmarks) · `R2-GLOBAL-DOCUMENTATION-MAP.md` (U2) · `README.md` raíz (M8) · `PROJECT-DOCUMENTATION-STATUS.md` (K3) · `POLARIS12-MAP.md` (M4,claims verificados/no verificados)

## 5. Elementos que deben permanecer intactos

| Elemento | Motivo |
|---|---|
| **Los 10 scripts de Set H** | protegidos; 10/10 SHA256 intactos; NO-GO operativo |
| `00-INDICE/REORGANIZACION-MANIFEST.sha256` | evidencia de integridad pre-movimiento |
| `REORGANIZATION-AUDIT.md`, `POST-REORGANIZATION-*.md`, `REGISTRO-*.md` | bitácora de la reparación (A–G + Set I) |
| Artefactos CMake/Ninja generados (2 harnesses) |“F”; se regeneran, no se editan |
| `m1-schedule.json`, `state_*.txt`, `manifest.*`, `audit.json`, `stdout/stderr/log` |“F”; evidencia de corridas |
| Los 2 `power-sweep-*` |“F”; no editables, requieren reconstrucción |
| `/home/lucas/Escritorio/RX550-INVESTIGACION-NOTEBOOKLM/` (50 copias) | “F”; copia plana, no symlinks |
| `RX550_Iterative_Research/`, `RX550_Modo_Torneo_Backup_2026-09-19_0836/` | “B”; evidencia histórica |
| Las 36+M y 10 `??` actuales | sin commit hasta revisión humana |

## 6. Elementos que requieren decisión humana

| # | Decisión | Por qué no puede decidirse automáticamente |
|---|---|---|
| D1 | **Papel de `00-INDICE/README.md`**: índice vivo o snapshot histórico | Afecta a si C1–C5 se reparan o se marcan como intencionadas |
| D2 | **U2 — `R2-GLOBAL-DOCUMENTATION-MAP.md`**: actualizar como mapa vivo o congelar como histórico | El documento se autodeclara mapa de navegación activo |
| D3 | **U4 — `BENCHMARK-INVENTORY.md`**: reconciliar estados de benchmarks o congelar | Requiere decidir qué benchmark se considera instalado/ejecutado |
| D4 | **U5 — `MASTER-PLAN.md:781`**: corregir la descripción `experiments/` o dejarla | Excluido del Set I por decisión previa |
| D5 | **Los 3 ficheros `M` con hash = manifiesto pre-movimiento** | Revertido o cambio no registrado; requiere historial de intención |
| D6 | **Estado canónico de R-4B** y si se promote a `SUPPORTED` | Evidencia n=1..3 insuficiente |
| D7 | **Recuperación de la evidencia `/tmp/opencode/` de R-4B** | Si no se recupera, la PARADA D queda como causa no verificable |
| D8 | **Reparación estática de Set H** (autorización específica) | Rompería la reproducibilidad histórica de 10 scripts |
| D9 | **Los 12 localizadores `/tmp/opencode/`** | Reubicar al repo, marcar como históricos, o aceptar pérdida |
| D10 | **Commit de los 36 `M` + 10 `??`** | Acción explícitamente diferida |

---

**Fin de la auditoría.** No se modificó ningún fichero existente. No se ejecutó ningún script del proyecto. No se hizo commit. Quedo a la espera de revisión antes de escribir cualquier reparación.
