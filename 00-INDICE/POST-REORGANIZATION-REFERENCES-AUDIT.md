# POST-REORGANIZATION-REFERENCES-AUDIT

> Auditoría documental de referencias **post-reorganización** de la raíz
> `~/Escritorio/RX550-INVESTIGACION/` (política documental permanente, estructura
> `00-INDICE/ 01-AUDITORIA/ 02-ARQUITECTURA/ 03-EXPERIMENTOS/ 04-IMPLEMENTACION/ 05-FUENTES-EXTERNAS/`).
>
> **Fase:** AUDITORÍA SOLO-LECTURA. **No se modificó ningún documento existente.**
> **Fecha:** 2026-09-23. **Estado:** clasificación completa; correcciones PROPUESTAS, no aplicadas.
> **Cobertura:** raíz completa (1.654 archivos, excl. `.git`), movida desde
> `~/Escritorio/RX550_Iterative_Research/` (1.651 archivos) + power-sweep home (388) + 3 baseline.

---

## 1. Metodología

1. **Inventario estructural** (`find`): 1.654 archivos, 0 enlaces simbólicos
   (`find -type l` = 0), sin `.git` en el conteo.
2. **Detección de hipervínculos Markdown**: `grep -rl '\]('` sobre los 178 `.md`
   → **0 archivos con hipervínculos `[texto](ruta)` en todo el árbol**.
   → Todas las referencias son **textuales** (rutas en backticks/prosa/comandos),
   no enlaces navegables. Esto invalida la "resolución de links relativos" como
   mecanismo: la corrección sería edición textual de rutas.
3. **Búsqueda de patrones** (`grep -roI`, binarios excluidos, excl. `.git`):
   - `RX550_Iterative_Research`
   - `RX550_Benchmarks`
   - `experiments/` (segmento de ruta antigua)
   - `/home/lucas` (rutas absolutas antiguas)
   - `Escritorio/`
   - `../` (relativas potencialmente afectadas)
   - `~/`
4. **Revisión por archivo** (línea y contexto) de toda la capa de documentación
   viva (`.md`/`.txt` documentales) y de los 25 `.sh` + 19 `.py`.
5. **Comprobación estructural** (FASE 5): manifests internos, READMEs internos,
   scripts con `PYTHONPATH`/rutas relativas — **sin ejecutar** nada.
6. **Clasificación A–F** de cada referencia y **mapeo origen → destino actual**
   usando el mapa oficial de la reorganización (los 8 grupos y las 5 asignaciones
   puntuales registradas en `REGISTRO-DE-MOVIMIENTOS.md`).
7. **Regla de no-invención**: toda referencia cuyo destino no pudo determinarse
   con seguridad quedó marcada **UNKNOWN/AMBIGUO (E)**, sin solución inventada.

---

## 2. Cantidad total de referencias encontradas

Instancias exactas por patrón (archivos de texto, `.git` excluido, binarios excluidos):

| Patrón | Instancias totales | Sin `REORGANIZACION-MANIFEST.sha256` | Archivos de texto afectados (sin manifest) |
|---|---|---|---|
| `RX550_Iterative_Research` | 1.511 | **253** | 67 |
| `/home/lucas` | 3.034 | **1.387** | 82 |
| `experiments/` | 1.607 | **440** | n/a (ver §7) |
| `Escritorio/` | 1.568 | **310** | n/a (ver §7) |
| `RX550_Benchmarks` | 13 | **13** | 3 (MASTER-PLAN, REORGANIZATION-AUDIT, REGISTRO) |
| `../` | 1.547 | **1.547** | mayormente registros sysfs y segmentos `/opt/.../...` |
| `~/` | 85 | **85** | n/a |
| **Σ (sin manifest, solapado)** | | **≈ 4.035** | (~110–120 archivos documentales + artefactos) |

Notas:
- Las instancias se **solapan** (una línea puede contener varios patrones, p.ej.
  `/home/lucas/Escritorio/RX550_Iterative_Research/experiments/...`).
- El `REORGANIZACION-MANIFEST.sha256` aporta 1.258 de las 1.511 instancias de
  `RX550_Iterative_Research` (rutas ORIGEN históricas, ver §9 — no se toca).
- El grueso de las restantes vive en **artefactos de build** y **logs de
  ejecución** (categoría C/evidencia, §6), no en documentación viva.

---

## 3. Referencias a `RX550_Iterative_Research` (253 sin manifest, 67 archivos)

Desglose por clase:

### 3.1 Artefactos de build generados (evidencia de compilación en el sitio antiguo) — C
| Archivo | Instancias |
|---|---|
| `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/harness/build/build.ninja` | 37 |
| `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/harness/build/build.ninja` | 22 |
| `…/harness/build/CMakeCache.txt` (R4B y R4C) | 6 + 6 |
| `…/harness/build/CMakeFiles/CMakeConfigureLog.yaml` (R4B y R4C) | 5 + 5 |
| `…/harness/build/CMakeFiles/TargetDirectories.txt` (R4B y R4C) | 5 + 6 |
| `…/harness/build/cmake_install.cmake` (R4B y R4C) | 3 + 3 |
| `…/harness/build/CMakeFiles/rules.ninja` (R4B y R4C) | 2 + 3 |
| `…/harness/build/CTestTestfile.cmake` (R4B y R4C) | 2 + 2 |
| `…/harness/build/CMakeFiles/InstallScripts.json` (R4B y R4C) | 1 + 1 |
| `…/harness/build/.ninja_log` (R4B y R4C) | 2 + 2 |
| `…/harness/build/.ninja_deps`, `*.o`, `*.so`, binarios, `*.spv` | (binarios, no contados) |

Estos archivos incrustan rutas absolutas **del momento de compilación**. Son
evidencia del build (cómo se compiló, dónde). **No se corrigen a mano**: si algún
día se recompila, se regenera con `cmake`/`ninja` desde la nueva ubicación.

### 3.2 Logs y configs de ejecución (evidencia de runtime) — C
`results/logs/*.log` (session1/2-v22/v23, *.phase1.log, trial_gov*.log, trial_dist*.log,
nohup), `harness.log`, `log.txt` (minitest/rep1-2), `orquestador.log`,
`ab-e5.log`, `stdout_200k.log`, resultados `results/*_config.txt` (8 archivos R4C,
2 refs c/u), `m1-schedule.json` (10 + 1).

Registran con precisión QUÉ y DÓNDE se ejecutó. Históricos inmutables. **No se tocan.**

### 3.3 Scripts de experimento con ruta absoluta antigua — A (ver §7.6 y §10)
`telemetria.sh` (R4B y EXPLORATORIO), `soak-probe.sh`, `soak-final.sh`,
`orquestador.sh`, `run_superposition.sh`, `analizar_etapa2.py`,
`auditoria_reconstruccion.py` → código con `OUT/BASE/WORK/SCR` = ruta vieja.

### 3.4 Documentación viva con la ruta absoluta antigua — A/E (detalle en §7)
`MASTER-PLAN.md:59`, `R2-GLOBAL-DOCUMENTATION-MAP.md:23`,
`R2-HISTORICAL-EXPERIMENT-INVENTORY.md:20`, `FASE-D-ETAPA-2-PLAN.md:213`,
`FASE-D-ETAPA-3-PRECHECK.md:228–229`, `README-FASE2.md:83`, `README-FASE3.md:144`.

### 3.5 Históricas deliberadas — C
`REORGANIZATION-AUDIT.md` (3), `REGISTRO-DE-MOVIMIENTOS.md` (1),
`R2-HISTORICAL-EXPERIMENT-INVENTORY.md:19–20` (ubicación del inventario
histórico del repositorio ORIGINAL).

---

## 4. Referencias a `RX550_Benchmarks` (13)

| # | Archivo:Línea | Referencia | Clasificación | Acción propuesta | Confianza |
|---|---|---|---|---|---|
| 1 | `00-INDICE/MASTER-PLAN.md:82` | "RX550_Benchmarks: **GravityMark 1.89**… instalados exclusivamente en `~/Escritorio/berchmark/instalados/`" | **D** (procedencia + destino externo real) | Sin cambio | Alta |
| 2 | `00-INDICE/MASTER-PLAN.md:109` | "Inventario de benchmarks para M2 → `~/Escritorio/RX550_Benchmarks/BENCHMARK-INVENTORY.md`" | **A** (ruta absoluta antigua) | → `~/Escritorio/RX550-INVESTIGACION/05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md` | Alta |
| 3 | `00-INDICE/MASTER-PLAN.md:111` | "registradas en `RX550_Benchmarks/docs/` (`SOURCES-AND-EXECUTION.md`, `DOWNLOAD-MANIFEST.sha256`, `README.md`)" | **A** (prefijo sin raíz, hoy inválido) | → `05-FUENTES-EXTERNAS/RX550_Benchmarks/docs/…` | Alta |
| 4–13 | `00-INDICE/REORGANIZATION-AUDIT.md:17,44,147,148,149,150,214` | Auditoría pre-movimiento (inventario, duplicado `GravityMark_1.89.run` `de090c7b…`, propuesta MOVER) | **C** (históricas) | Sin cambio | Alta |

**Conclusión FASE 4:** las 13 referencias se agrupan en **2 vivas a reparar**
(MASTER-PLAN:109/111 → deben apuntar a
`05-FUENTES-EXTERNAS/RX550_Benchmarks/…`) y **11 históricas/registro** que
permanecen. Ninguna referencia a `RX550_Benchmarks` debe quedar como ruta externa
fuera de la raíz, porque **el propio directorio se movió dentro de la raíz** a
`05-FUENTES-EXTERNAS/RX550_Benchmarks/`. Las referencias a
`~/Escritorio/berchmark/…` (software instalado, 22 en BENCHMARK-INVENTORY, varias
en MASTER-PLAN/STATUS) **sí son externas y se mantienen** (D).

---

## 5. Referencias relativas potencialmente afectadas

**Hallazgo principal:** no hay hipervínculos Markdown, por lo que no existen
"links relativos rotos" como mecanismo. Las rutas relativas que existen son
textuales:

- **Válidas sin cambio (B):**
  - `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/run_thermal_replicate.sh:15`
    `EXP="$BASE/../FASE-R4B-GOVERNOR"` → sigue resolviendo (hermanas bajo `03-EXPERIMENTOS/`) ✓
  - `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/harness/run_all.sh:6`
    `BASE="$(dirname "$0")/.."` ✓
  - `05-FUENTES-EXTERNAS/RX550_Benchmarks/docs/DOWNLOAD-MANIFEST.sha256`
    `../official-downloads/gravitymark/GravityMark_1.89.run` ✓ (relativa interna,
    se movió el árbol completo)
  - launcher torneo `04-IMPLEMENTACION/rx550-torneo/rx550-torneo`:
    `HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`; `PYTHONPATH="$HERE/src"` ✓ (relativa)
  - tests torneo `run_tests*.py`: `SRC` relativo a `src/` + `sys.path` ✓
  - scripts `run_all_v22/v23.sh`, `run_all.sh` (R4B), `run-m1.sh`,
    `run_one.sh` (fase-a/b), `driver.sh`: rutas relativas a su propio directorio ✓
- **Rotas textuales (A):** la gran mayoría de referencias `experiments/<X>/…`
  de §7, y `README-FASE1.md:3` `../RX550_BUILD_SPECIFICATION.txt` (desde
  `04-IMPLEMENTACION/rx550-torneo/` ya NO lleva a la raíz).
- **No afectadas por el movimiento (D/C):** segmentos `/opt/.../...`,
  `/usr/lib64/...`, `VK_ICD_FILENAMES=.../radeon_icd...` (externos); registros de
  symlinks sysfs `../../devices/pci*` en `state_*.txt`/`CONDICIONES.txt`
  (evidencia de captura, C).

**Comprobación estructural de scripts sin ejecutar (FASE 5):**
- Torreo (CLI operativa): launcher + `src/rx550_torneo/*.py` usan rutas relativas
  (`$HERE`, `os.path` sobre el paquete, `XDG_STATE_HOME`) y sysfs
  (`/sys/class/drm`, `/dev/dri`) → **el movimiento no rompió nada de torneo**.
- `state_manager.py`: rutas de estado relativas/entorno, sin rutas absolutas del
  repo antiguo → ✓.

---

## 6. Clasificación A–F (definiciones y distribución)

| Tipo | Definición | Volumen estimado | ¿Se modifica? |
|---|---|---|---|
| **A** — claramente rota | Rutas documentales vivas y código que tras el movimiento ya no apuntan al contenido | ≈ 95 líneas en ~30 archivos doc + ~13 en 9 scripts | **Proponer edición** (§10) |
| **B** — válida sin cambio | Rutas relativas que siguen resolviendo | ~15 (scripts relativos, DOWNLOAD-MANIFEST, launcher, tests) | No |
| **C** — histórica deliberada | Manifest de reorganización, REGISTRO, REORGANIZATION-AUDIT, logs, datos, build, configs de runtime, m1-schedule, state files, procedencia RX550_Benchmarks | ≈ 3.500+ instancias | **No, jamás** |
| **D** — externa | `~/Escritorio/berchmark/…`, `/opt/mesa-26.2.2-rx550-haswell`, `/usr/lib64`, sysfs, `VK_ICD_FILENAMES`, URLs | ≈ 500+ | No |
| **E** — ambigua | Refs cuyo destino correcto requiere decisión (ver §8) | ≈ 10 | Decidir en fase de reparación |
| **F** — artefacto fuera de la raíz | Backup histórico, NotebookLM, PROYECTOS_LUCAS, exportes `~/Escritorio/*.txt`, power-sweep home, `/tmp/rx550*` | ≈ 30 (docs) | **No; mantener como refs externas** |

---

## 7. Tabla archivo → referencia → corrección propuesta

Convención de mapeo de destinos (según plan ejecutado):

| Prefijo histórico | Destino actual |
|---|---|
| `experiments/AUDIT-001/` | `01-AUDITORIA/AUDIT-001/` |
| `experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/` | `01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/` |
| `experiments/FASE-R2-PROJECT-DOCUMENTATION/` | `01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION/` (salvo `R2-GLOBAL-DOCUMENTATION-MAP.md` → `00-INDICE/`; `FASE-{E..Q}-DESIGN.md` y EXPERIMENT-PRIORITY-MATRIX → `04-IMPLEMENTACION/`) |
| `experiments/FASE-R3-NOVELTY-AUDIT/` | `01-AUDITORIA/FASE-R3-NOVELTY-AUDIT/` |
| `experiments/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/` | `01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/` |
| `experiments/IMPLEMENTATION-READINESS/` | `01-AUDITORIA/IMPLEMENTATION-READINESS/` |
| `experiments/POLARIS12-MAP/` | `02-ARQUITECTURA/POLARIS12-MAP/` |
| `experiments/FASE-R0-EXTERNAL-KNOWLEDGE/` | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/` |
| `experiments/FASE-R4{A,B,C}-…/`, `FASE-D-COUNTERS-AUDIT/`, `R-14-…/`, `M1-cap-35-30/`, `fase-a-…/`, `fase-b-…/`, `ep05-…/`, `ep06-…/`, `WORKLOAD-SINTETICO/`, `EXPLORATORIO-GravityMark/`, `results/` | `03-EXPERIMENTOS/<mismo nombre>` |
| `projects/` | `04-IMPLEMENTACION/projects/` |
| `rx550-torneo/` | `04-IMPLEMENTACION/rx550-torneo/` |

### 7.1 `00-INDICE/` (documentación viva)

| Archivo:Línea(s) | Referencia | Tipo | Corrección propuesta | Conf. |
|---|---|---|---|---|
| `MASTER-RESEARCH-STATUS.md:35–36,54,108,129,149,169,211,235,255,281` | `experiments/<dir>/…` (fase-a, POLARIS12-MAP, AUDIT-001, R0, R1, R2, R3-1, R4A, R4C, R4B) | A | Aplicar tabla de mapeo → `../03-EXPERIMENTOS/…`, `../01-AUDITORIA/…`, `../02-ARQUITECTURA/…` | Alta |
| `MASTER-RESEARCH-STATUS.md:365–387` | Índice de experimentos con `experiments/…` | A | Idem (filas 365–387) | Alta |
| `MASTER-RESEARCH-STATUS.md:407,424,438,442` | `experiments/FASE-R4B…`, `FASE-D…`, `R1-1…`, `POLARIS12-MAP…` | A | Idem | Alta |
| `MASTER-RESEARCH-STATUS.md:50,388` | `~/Escritorio/berchmark/instalados/` | D | **Sin cambio** | Alta |
| `MASTER-PLAN.md:59` | `~/Escritorio/RX550_Iterative_Research/rx550-torneo/` + `experiments/` | A | → `04-IMPLEMENTACION/rx550-torneo/` + `03-EXPERIMENTOS/` | Alta |
| `MASTER-PLAN.md:290` | `experiments/POLARIS12-MAP/POLARIS12-MAP.md` | A | → `../02-ARQUITECTURA/POLARIS12-MAP/POLARIS12-MAP.md` | Alta |
| `MASTER-PLAN.md:325,338,728` | `experiments/FASE-D…`, `FASE-R1…` | A | → `../03-EXPERIMENTOS/…`, `../01-AUDITORIA/…` | Alta |
| `MASTER-PLAN.md:774,781` | `experiments/FASE-R2…` + `projects/` | A | → `../01-AUDITORIA/FASE-R2…` + `../04-IMPLEMENTACION/projects/` | Alta |
| `MASTER-PLAN.md:82,104` | `~/Escritorio/berchmark/instalados/` | D | **Sin cambio** | Alta |
| `MASTER-PLAN.md:109,111` | `~/Escritorio/RX550_Benchmarks/…`, `RX550_Benchmarks/docs/…` | A | → `05-FUENTES-EXTERNAS/RX550_Benchmarks/…` | Alta |
| `README.md:25–29` | `experiments/fase-a…, fase-b…, ep06…, ep05…, M1…` | A | → `../03-EXPERIMENTOS/…` | Alta |
| `README.md:8` | `RX550_BUILD_SPECIFICATION.txt` (hoy en `02-ARQUITECTURA/`) | A | → `../02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` | Alta |
| `README.md:6` | `FINAL-RESEARCH-STATUS.md` (misma carpeta) | B | Sin cambio ✓ | Alta |
| `README.md:31` | `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/` | F | **Sin cambio** | Alta |
| `PROJECT-DOCUMENTATION-STATUS.md:9` | `experiments/FASE-R2-PROJECT-DOCUMENTATION/R2-GLOBAL-DOCUMENTATION-MAP.md` | A | → `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` (asignación puntual) | Alta |
| `PROJECT-DOCUMENTATION-STATUS.md:24,26` | `experiments/fase-a…`, `experiments/POLARIS12-MAP/` | A | → `../03-EXPERIMENTOS/…`, `../02-ARQUITECTURA/…` | Alta |
| `PROJECT-DOCUMENTATION-STATUS.md:61` | `~/Escritorio/berchmark/instalados/` | D | **Sin cambio** | Alta |
| `FINAL-RESEARCH-STATUS.md:12` | `experiments/M1-cap-35-30/RESULTADOS-M1.md` | A | → `../03-EXPERIMENTOS/…` | Alta |
| `FINAL-RESEARCH-STATUS.md:17` | `/opt/mesa-26.2.2-rx550-haswell` | D | **Sin cambio** | Alta |
| `decisions.md:41` | `experiments/WORKLOAD-SINTETICO/RESEARCH.md` | A | → `../03-EXPERIMENTOS/…` | Alta |
| `experiments_proposed.md:15` | `experiments/M1-cap-35-30/RESULTADOS-M1.md` | A | → `../03-EXPERIMENTOS/…` | Alta |
| `R2-GLOBAL-DOCUMENTATION-MAP.md:23` | "Raíz del repositorio (`/home/lucas/Escritorio/RX550_Iterative_Research/`)" | E | Decidir: actualizar a la nueva raíz (mapa vivo) o anotar como snapshot histórico (ver §8.2) | Media |
| `R2-GLOBAL-DOCUMENTATION-MAP.md:44,172,174` | "Capa `experiments/`", distribución en 4 capas | E | Idem §8.2 | Media |
| `R2-GLOBAL-DOCUMENTATION-MAP.md:148,154` | Backup + power-sweep home | F | **Sin cambio** | Alta |
| `REORGANIZATION-AUDIT.md` (todos) | Rutas PRE-movimiento (auditoría histórica) | C | **Sin cambio** | Alta |
| `REGISTRO-DE-MOVIMIENTOS.md` (todos) | Registro de la ejecución | C | **Sin cambio** | Alta |
| `REORGANIZACION-MANIFEST.sha256` | 1.258 rutas ORIGEN | C | **Sin cambio** (base histórica de verificación) | Alta |

### 7.2 `01-AUDITORIA/`

| Archivo:Línea | Referencia | Tipo | Corrección propuesta | Conf. |
|---|---|---|---|---|
| `FASE-R1-DOCUMENTATION-RECONCILIATION/R1-1-GFX8-EVENT-RECONCILIATION.md:143` | `experiments/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-ID-REFERENCE.txt` | A | → `../../05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/…` | Alta |
| `FASE-R1-DOCUMENTATION-RECONCILIATION/FASE-R1-FINAL-REPORT.md:5,106` | `experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/` (directorio propio) | A | → `../../01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/` | Alta |
| `FASE-R2-PROJECT-DOCUMENTATION/FASE-R2-FINAL-REPORT.md:7` | Directorio propio | A | → `../../01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION/` | Alta |
| `FASE-R2-PROJECT-DOCUMENTATION/FASE-R2-FINAL-REPORT.md:46,64,185` | Backup + `experiments/` A–D/R-0/R-1 + directorio propio | C/A | Backup: sin cambio; resto: mapear | Media |
| `FASE-R2-PROJECT-DOCUMENTATION/R2-HISTORICAL-EXPERIMENT-INVENTORY.md:19,30,54,194–196` | Backup Torneo (`/home/lucas/…_Backup_…/experiments/`) | F | **Sin cambio** (inventario histórico deliberado) | Alta |
| `R2-HISTORICAL-EXPERIMENT-INVENTORY.md:20,38,112` | `experiments/WORKLOAD-SINTETICO/`, `experiments/M1-cap-35-30/` (repo) | E | Decidir: actualizar a `03-EXPERIMENTOS/…` o anotar (ver §8.3) | Media |
| `FASE-R3-NOVELTY-AUDIT/FASE-R3-FINAL-REPORT.md:7` | `experiments/FASE-R3-NOVELTY-AUDIT/` + `projects/` | A | → `../../01-AUDITORIA/…` + `../../04-IMPLEMENTACION/projects/` | Alta |
| `FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/README.md:3` | Directorio propio `experiments/FASE-R3-1-…/` | A | → `../../01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/` | Alta |
| `FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/FUSION-03-INVERTED-MEMORY-HIERARCHY.md:32` | `experiments/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md` | A | → `../../03-EXPERIMENTOS/FASE-R4A-BANDWIDTH-REAL/…` | Alta |
| `AUDIT-001/AUDIT-001.md:256` | `experiments/POLARIS12-MAP/` | A | → `../../02-ARQUITECTURA/POLARIS12-MAP/` | Alta |
| `AUDIT-001/*` (84,146, etc.) | `/opt/mesa-…`, `/usr/lib64/…` | D | **Sin cambio** | Alta |

### 7.3 `02-ARQUITECTURA/`

| Archivo:Línea | Referencia | Tipo | Corrección propuesta | Conf. |
|---|---|---|---|---|
| `evidence.md:8,9,10,11,12` | `experiments/fase-a…`, `fase-b…`, `ep06…`, `ep05…` | A | → `../03-EXPERIMENTOS/…` | Alta |
| `evidence.md:25` | Backup `experiments/mesa-e1-…`, `mesa-e3-…` | F | **Sin cambio** (backup histórico) | Alta |
| `evidence.md:3` | Backup `~/Escritorio/…_Backup_…/` | F | **Sin cambio** | Alta |
| `research_log.md:43` | `experiments/M1-cap-35-30/RESULTADOS-M1.md` | A | → `../03-EXPERIMENTOS/…` | Alta |
| `research_log.md:8` | Backup | F | **Sin cambio** | Alta |
| `RX550_BUILD_SPECIFICATION.txt:79,304,305` | `/opt/mesa-…`, `/usr/lib64/…` | D | **Sin cambio** | Alta |

### 7.4 `03-EXPERIMENTOS/` (documentación interna)

| Archivo:Línea | Referencia | Tipo | Corrección propuesta | Conf. |
|---|---|---|---|---|
| `FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL.md:3` | Directorio propio `experiments/FASE-R4B-GOVERNOR/` | A | → `../FASE-R4B-GOVERNOR/` (misma carpeta) | Alta |
| `FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL-v2.2.md:10` | `experiments/FASE-R4B-THERMAL-TEST/` | A | → `../FASE-R4B-THERMAL-TEST/` | Alta |
| `FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md:33,35,37,39,41,42` | `experiments/fase-a…/RESULTADOS-FASE-A.md`, `fase-b…/RESULTADOS-FASE-B.md`, `ep06…/RESULTADOS-EP06.md`, `AUDIT-001/METRICS-DEFINITIONS.md`, `FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL.md`, `…-RESULTADOS.md` | A | → `../fase-a-…`, `../ep06-…`, `../AUDIT-001` no existe → `../../01-AUDITORIA/AUDIT-001/…`, `../FASE-R4B-GOVERNOR/…` | Alta |
| `FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md:11` | `experiments/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/FUSION-01-…` | A | → `../../01-AUDITORIA/FASE-R3-1-…/FUSION-01-…` | Alta |
| `FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md:15` | `experiments/FASE-R2-PROJECT-DOCUMENTATION/FASE-P-…-DESIGN.md` | A | → `../../04-IMPLEMENTACION/FASE-P-FRAME-GENERATION-UPSCALING-DESIGN.md` | Media |
| `FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md:115` | "Sin escribir fuera de `experiments/FASE-R4C-JITTER-OBSERVABILITY/`" | C | Sin cambio (declaración de alcance en su momento) | Alta |
| `FASE-R4C-JITTER-OBSERVABILITY/EXP-F1-A-RESULTADOS.md:10,152` | `experiments/FASE-R4C-JITTER-OBSERVABILITY/harness/` + `results/` (propio) | A | → `../harness/`, `../results/` | Alta |
| `R-14-SUPERPOSITION-DISSECTION/R-14-SUPERPOSITION-DISSECTION.md:153` | `experiments/R-14-SUPERPOSITION-DISSECTION/` (propio) | A | → `../R-14-SUPERPOSITION-DISSECTION/` | Alta |
| `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-PLAN.md:213` | `WORK=/home/lucas/Escritorio/RX550_Iterative_Research`; runs en `${WORK}/experiments/FASE-D-…/runs/etapa2/…` | A | → base relativa al script; runs → `../runs/etapa2/…` | Alta |
| `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-PLAN.md:229` | `$WORK/experiments/EXPLORATORIO-GravityMark/telemetria.sh` | A | → `../EXPLORATORIO-GravityMark/telemetria.sh` | Alta |
| `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-PLAN.md:244,257` | `cd …/berchmark/instalados/Unigine_Superposition-1.1/bin`; `cd $WORK/experiments/WORKLOAD-SINTETICO` | D/A | berchmark: **sin cambio**; WORKLOAD → `../WORKLOAD-SINTETICO` | Alta |
| `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-PRECHECK.md:228,229` | `sudo umr … > /home/lucas/Escritorio/RX550_Iterative_Research/experiments/FASE-D-…/runs/snapshot-….txt` | A | → salida relativa `../runs/snapshot-….txt` | Alta |
| `FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md:174,188` | `experiments/FASE-R0-EXTERNAL-KNOWLEDGE/`, `experiments/FASE-R1-…/R1-1-…` | A | → `../../05-FUENTES-EXTERNAS/…`, `../../01-AUDITORIA/…` | Alta |
| `FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md:30` | `/home/lucas/**` (docs personales) | D | **Sin cambio** | Alta |
| `WORKLOAD-SINTETICO/RESEARCH.md:225` | `experiments/WORKLOAD-SINTETICO/src/compute.comp` (propio) | A | → `src/compute.comp` | Alta |
| `WORKLOAD-SINTETICO/RESEARCH.md:712` | `experiments/EXPLORATORIO-GravityMark/telemetria.sh` | A | → `../EXPLORATORIO-GravityMark/telemetria.sh` | Alta |
| `EXPLORATORIO-GravityMark/runs/RESULTADO.md:12,21` | `.../GravityMark_1.89/bin`, `.../runs/200k/stdout_200k.log` | B | Sin cambio (notación `.../` relativa interna ✓) | Alta |
| `ep05-mesa-custom-…/RESULTADOS-EP05.md:16` y datos | `/opt/mesa-…`, `VK_ICD_FILENAMES=...` | D | **Sin cambio** | Alta |

### 7.5 `04-IMPLEMENTACION/`

| Archivo:Línea | Referencia | Tipo | Corrección propuesta | Conf. |
|---|---|---|---|---|
| `rx550-torneo/README-FASE1.md:3` | `../RX550_BUILD_SPECIFICATION.txt` | A | → `../../02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` | Alta |
| `rx550-torneo/README-FASE2.md:83` | `cd ~/Escritorio/RX550_Iterative_Research/rx550-torneo` | E | Decidir destino operativo (ver §8.1) | Media |
| `rx550-torneo/README-FASE3.md:144` | ídem | E | Ídem §8.1 | Media |
| `rx550-torneo/README-M1.md` | — | — | Sin referencias afectadas ✓ | — |
| `SYNTHETIC-WORKLOAD-DESIGN.md:6` | "prototipo existente `experiments/WORKLOAD-SINTETICO/`" | A | → `../03-EXPERIMENTOS/WORKLOAD-SINTETICO/` | Alta |
| `FASE-E-REAL-GAME-BASELINE-DESIGN.md:31` | `experiments/R-14-SUPERPOSITION-DISSECTION/` | A | → `../03-EXPERIMENTOS/R-14-…/` | Alta |
| `FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md:7` | `experiments/POLARIS12-MAP/EXPERIMENT-CANDIDATES.md` | A | → `../02-ARQUITECTURA/POLARIS12-MAP/…` | Alta |
| `projects/*/README.md` (8) | — | — | Sin referencias afectadas ✓ | — |
| `rx550-torneo/rx550-torneo` (launcher) | `$HERE/src` (PYTHONPATH relativo) | B | Sin cambio ✓ | Alta |
| `rx550-torneo/src/…/*.py` | sysfs `/sys`,`/dev` + rutas relativas | B/D | Sin cambio ✓ | Alta |
| `rx550-torneo/tests/run_tests*.py` | `SRC` relativo + `sys.path` | B | Sin cambio ✓ | Alta |

### 7.6 `05-FUENTES-EXTERNAS/` y scripts

| Archivo:Línea | Referencia | Tipo | Corrección propuesta | Conf. |
|---|---|---|---|---|
| `BENCHMARK-INVENTORY.md` (22) | `~/Escritorio/berchmark/…` | D | **Sin cambio** (software instalado externo) | Alta |
| `FASE-R0-EXTERNAL-KNOWLEDGE/FASE-R0-EXTERNAL-KNOWLEDGE-FINAL-REPORT.md:7` | (`experiments/FASE-R0-EXTERNAL-KNOWLEDGE/`) propio | A | → `../../05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/` | Alta |
| `FASE-R0-EXTERNAL-KNOWLEDGE/R0-2-POWERPLAY-MCLK-SMU7.md:25,114` | `experiments/WORKLOAD-SINTETICO/` | A | → `../../03-EXPERIMENTOS/WORKLOAD-SINTETICO/` | Alta |
| `RX550_Benchmarks/README.md`, `docs/` | — | B | Sin referencias afectadas ✓ | — |
| **Scripts:** `telemetria.sh` (R4B:9, EXPLORATORIO:4) | `OUT=${2:-/home/lucas/Escritorio/RX550_Iterative_Research/experiments/…/results|runs/telemetria.csv}` | A | → `$(dirname "$0")/results|runs/telemetria.csv` | Alta |
| `soak-probe.sh:4`, `soak-final.sh:4` | `SCR=/home/lucas/Escritorio/RX550_Iterative_Research/experiments/fase-b-…/scripts` | A | → `../fase-b-cap-probe-20260919-122038/scripts` (relativo, hermanas bajo 03) | Alta |
| `orquestador.sh:5,6,29,105` (+:76 berchmark) | `WORK=…/RX550_Iterative_Research`; `$WORK/experiments/EXPLORATORIO-GravityMark/…`; `cd $WORK/experiments/WORKLOAD-SINTETICO` | A (+D) | → rutas relativas al script; berchmark sin cambio | Alta |
| `analizar_etapa2.py:6`, `auditoria_reconstruccion.py:7` | `BASE="/home/lucas/…/RX550_Iterative_Research/experiments/FASE-D-…/runs/etapa2"` | A | → derivar de `__file__` o ruta relativa | Alta |
| `run_superposition.sh:6,15` | `OUTDIR=${2:-…/R-14-…/runs/…}`; telemetria EXPLORATORIO | A | → relativas a `$(dirname "$0")` y `../EXPLORATORIO-GravityMark/…` | Alta |
| `run_superposition.sh:19` | `cd …/berchmark/instalados/Unigine_Superposition-1.1/bin` | D | **Sin cambio** | Alta |
| `run_thermal_replicate.sh:6`, `run_all.sh` (R4C):3 | Comentarios "experiments/FASE-R4B-THERMAL-TEST/…", "experiments/FASE-R4C-…/" | A (solo comentario) | Actualizar comentario o dejarlo (inocuo); código ✓ B | Media |

---

## 8. Casos ambiguos (E) — requieren decisión antes de tocar

1. **`README-FASE2.md:83` / `README-FASE3.md:144`** — `cd ~/Escritorio/RX550_Iterative_Research/rx550-torneo`: ¿debe apuntar a la copia movida `04-IMPLEMENTACION/rx550-torneo/` (launcher `$HERE/src`, herramientas de home `~/rx550-torneo`/`~/bin/rx550-torneo` son bash legacy distintos según REORGANIZATION-AUDIT §14)? Proposición inicial: apuntar a `~/Escritorio/RX550-INVESTIGACION/04-IMPLEMENTACION/rx550-torneo` + nota sobre launcher operativo. **UNKNOWN parcial**: cuál es la "herramienta operativa" de arranque normal del usuario no se puede afirmar desde la auditoría.
2. **`R2-GLOBAL-DOCUMENTATION-MAP.md`** — describe el árbol pre-movimiento (4 capas, `experiments/`). Es el "mapa de navegación para investigador nuevo"; tras la reorganización quedó desactualizado pero conserva valor histórico de inventario. Decidir: (a) actualizar a la nueva estructura (rol de mapa vivo) o (b) conservarlo como snapshot + referenciar el nuevo layout desde 00-INDICE. Proposición: (a) con nota de versión.
3. **`R2-HISTORICAL-EXPERIMENT-INVENTORY.md`** — inventario cuya finalidad incluye el repositorio ORIGINAL y el backup; sus refs `experiments/WORKLOAD-SINTETICO/` y `M1-cap-35-30/` apuntan a contenido ya movido. Decidir: actualizar rutas de contenido movido (conservando notas de origen) vs. dejarlo como documento histórico. Proposición: actualizar rutas de contenido movido + conservar las del backup.
4. **`00-INDICE/README.md` (antiguo README raíz)** — sigue siendo índice de navegación útil pero describe la estructura antigua y ahora duplica al nuevo `README.md` raíz. Decidir: actualizar rutas al nuevo layout (rol vigente) o declararlo histórico (nota + enlace al README raíz). UNKNOWN: no hay decisión previa registrada.
5. **`m1-schedule.json`** (2 archivos) — registro de ejecución (C) pero si se reutilizara operativamente contendría un `dir`/ruta antigua. Decidir en fase de reparación **no** (permanece C; el runner regenera schedules).
6. **Comentarios de ruta en scripts** (`run_thermal_replicate.sh:6`, `run_all.sh R4C:3`) — inocuos para ejecución; reparación opcional de estética. UNKNOWN si el usuario quiere tocar comentarios.

---

## 9. Casos que NO deben modificarse (regla explícita)

- **`00-INDICE/REORGANIZACION-MANIFEST.sha256`** — 1.258 rutas ORIGEN; base histórica de verificación de integridad. **Inmutable.**
- **`00-INDICE/REGISTRO-DE-MOVIMIENTOS.md`** — trazabilidad de la ejecución. Inmutable.
- **`00-INDICE/REORGANIZATION-AUDIT.md`** — auditoría pre-movimiento (todo su contenido es histórico/deliberado).
- **Artefactos de build** RM4B/R4C `harness/build/*` — evidencia de compilación; regenerar es la única vía válida si se recompila.
- **Logs y configs de ejecución** — `results/logs/*.log`, `*_config.txt`, `harness.log`, `log.txt`, `orquestador.log`, `ab-e5.log`, `stdout_*.log`, `m1-schedule.json`.
- **Datos** — CSV/TSV/lines (sin rutas del repo; las 203 instancias "path-like" viven en logs, no en datos).
- **Registros de symlinks sysfs** en `state_*.txt`/`CONDICIONES.txt` (`../../devices/…`) — captura de entorno.
- **README/READMEs de RUN?** — manifests run (`manifest.txt` ep05/ep06/fase-a/b): solo campos `run/date/cmd` con envs `/opt/mesa…` → externos, correctos.
- **`DOWNLOAD-MANIFEST.sha256`** — relativa interna válida ✓.
- **NotebookLM** (`~/Escritorio/RX550-INVESTIGACION-NOTEBOOKLM/`, `README.md` raíz:19, REORGANIZATION-AUDIT:16) — externa, plana 50 docs, **no tocar** (pendiente verificación de symlinks).
- **Backup histórico** (`RX550_Modo_Torneo_Backup_2026-09-19_0836/`) — externo, 31.584 f.
- **`~/Escritorio/berchmark/…`** — software instalado (D).
- **`PROYECTOS_LUCAS/`**, **exportes `~/Escritorio/*.txt`**, **`/tmp/rx550*`** — externos (F).
- **Mesa/kernel/VBIOS/PowerPlay/sysfs** — jamás se tocan.
- **Scripts HOME** `~/rx550-torneo`, `~/bin/rx550-torneo`, `~/rx550-power-sweep.sh[.bak]` — fuera de la raíz, intactos.

---

## 10. Lista exacta de modificaciones propuestas (fase siguiente, SOLO con aprobación)

Agrupación por commits/paquetes sugeridos (todos con edición restringida a rutas,
sin tocar contenido científico):

1. **Set A — Maestros vivos `00-INDICE/`** (7 archivos, ≈ 55 ediciones): `MASTER-RESEARCH-STATUS.md`, `MASTER-PLAN.md`, `README.md`, `PROJECT-DOCUMENTATION-STATUS.md`, `FINAL-RESEARCH-STATUS.md`, `decisions.md`, `experiments_proposed.md` → aplicar tabla de mapeo §7.1 (+ `MASTER-PLAN.md:109,111` para `RX550_Benchmarks`).
2. **Set B — `R2-GLOBAL-DOCUMENTATION-MAP.md`**: actualizar secciones 1–2 (raíz y `experiments/`) al nuevo layout, con nota de versión (§8.2).
3. **Set C — `01-AUDITORIA/`** (≈ 10 ediciones): `R1-1-…:143`, `FASE-R1-FINAL-REPORT:5,106`, `FASE-R2-FINAL-REPORT:7,64,185`, `FASE-R3-FINAL-REPORT:7`, `FASE-R3-1 README:3`, `FUSION-03:32`, `AUDIT-001:256`.
4. **Set D — `02-ARQUITECTURA/`** (≈ 9 ediciones): `evidence.md:8–12`, `research_log.md:43`.
5. **Set E — `03-EXPERIMENTOS/` doc interna** (≈ 18 ediciones): `EXP-F4-A-PROTOCOL:3`, `EXP-F4-A-PROTOCOL-v2.2:10`, `TEST-TERMICO-READONLY:33–42`, `PRECHECK-REPORT:11,15`, `EXP-F1-A-RESULTADOS:10,152`, `R-14:153`, `FASE-D-ETAPA-2-PLAN:213,229,257`, `FASE-D-ETAPA-3-PRECHECK:228–229`, `FASE-D-GFX8-EVENT-ID-AUDIT:174,188`, `WORKLOAD-SINTETICO/RESEARCH.md:225,712`.
6. **Set F — `04-IMPLEMENTACION/`** (≈ 5 ediciones): `README-FASE1:3`, `SYNTHETIC-WORKLOAD-DESIGN:6`, `FASE-E:31`, `FASE-F:7`; resolver E-§8.1 para `README-FASE2/3` (cd).
7. **Set G — `05-FUENTES-EXTERNAS/`** (3 ediciones): `FASE-R0-FINAL:7`, `R0-2-POWERPLAY:25,114`.
8. **Set H — scripts de experimento** (9 archivos, ≈ 13 ediciones): `telemetria.sh` ×2, `soak-probe.sh`, `soak-final.sh`, `orquestador.sh`, `analizar_etapa2.py`, `auditoria_reconstruccion.py`, `run_superposition.sh` → reemplazar rutas absolutas por relativas a `$(dirname "$0")`. Regularización opcional de comentarios (`run_thermal_replicate.sh:6`, `run_all.sh R4C:3`).
9. **Set I — decisión pendiente**: `R2-HISTORICAL-EXPERIMENT-INVENTORY.md` content-refs (§8.3) y rol de `00-INDICE/README.md` (§8.4).

**Quedan explícitamente FUERA de cualquier edición:** categorías C/D/F de §9
(manifest, REGISTRO, REORGANIZATION-AUDIT, artefactos de build, logs, datos,
backup, NotebookLM, berchmark, PROYECTOS_LUCAS, exportes, Mesa/sysfs).

---

## 11. Confirmación de no-modificación

Durante esta fase **no se editó, movió, renombró, borró ni sobrescribió ningún
documento existente** dentro de `~/Escritorio/RX550-INVESTIGACION/` ni fuera de
ella. Único archivo creado: **este informe** (`00-INDICE/POST-REORGANIZATION-REFERENCES-AUDIT.md`).
Sin ejecución de scripts, benchmarks, instalaciones ni cambios de sistema/Mesa/
kernel/VBIOS/PowerPlay/sysfs/NotebookLM. Árbol Git de la raíz: sin cambios por
esta fase (verificable con `git status`).

---

## Anexo — Integridad estructural (FASE 5)

- **Referencias de contenido existen**: cada `experiments/<X>/<f>` referenciado
  tiene su archivo en el destino según el mapeo §7 (verificación global de
  integridad previa: 1.651/1.651 hashes idénticos en su nueva ruta) → las
  correcciones de §10 son de RUTA, no de contenido.
- **Manifests internos coherentes**: `manifest.txt` (runs ep05) ✓; `manifest.json`
  (FASE-R4B) sin campos de ruta ✓; `frozen.sha256` ✓; `DOWNLOAD-MANIFEST.sha256`
  (relativa interna válida) ✓; `m1-schedule.json` (registro de ejecución, C) ✓.
- **READMEs internos**: 13 de 16 READMEs sin referencias afectadas; 3 con
  referencias a corregir (`README-FASE1:3`, `README-FASE2:83`, `README-FASE3:144`)
  + `FASE-R3-1/README.md:3`.
- **Scripts con PYTHONPATH/rutas relativas**: estructuralmente coherentes tras el
  movimiento (launcher `$HERE/src`, tests `sys.path` relativo, `state_manager.py`
  con rutas de estado relativas). **No ejecutados.**
- **Symlinks**: 0 en toda la raíz (nada que verificar/convertir en esta fase).
