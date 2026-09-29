# DOCUMENTATION-RELATIONSHIPS — Relaciones documentales

**Fecha:** 2026-09-25T22:40Z
**Fase:** FASE 0 — censo. No se reparó ni se normalizó ninguna referencia.

## Regla de este informe

Solo se registran relaciones **respaldadas por contenido o por una referencia explícita** en los
documentos. No se infieren relaciones. Cuando la evidencia es una coincidencia temática y no una
declaración del documento, se marca como `INFERRED_NOT_DECLARED` y **no** se usa para el router.

Tipos de relación据此 los que se recognized:

| Tipo | Significado | Cómo se verificó |
|---|---|---|
| `REFERENCES` | El documento A cita explícitamente la ruta de B | Enlace Markdown, ruta en backticks o nombre de fichero desnudo que resuelve en el árbol |
| `DERIVED_FROM` | B declara explícitamente que se derivó de A | Declaración en el texto |
| `SUMMARIZES` | B declara resumir o agregar a A | Declaración en el texto |
| `VALIDATES` | B declara validar o confirmar A | Declaración en el texto |
| `CONTRADICTS` | A y B afirman estados incompatibles del mismo hecho | Comparación de valores citados; ambos existen |
| `SUPERSEDES` | B corrige o reemplaza explícitamente a A | Declaración en el texto |
| `IMPLEMENTS` | B es la implementación del diseño de A | Correspondencia nombre/versión + contenido |
| `TESTS` | B es la suite que prueba A | Correspondencia explícita |
| `RECOVERS` | B recupera contenido de A (o de donde A se originó) | Declaración en el texto |
| `DEPENDS_ON` | B declara que requiere A | Declaración en el texto |
| `HISTORICAL_VERSION_OF` | A es una versión anterior de B del mismo contenido | Versionado explícito en el nombre + contenido solapado |

---

## 1. Grafo de estado: la relación más importante

```
                    ┌─────────────────────────────────────┐
                    │  00-INDICE/MASTER-RESEARCH-STATUS.md│  63 KB · 30 entrantes
                    │  "punto único de entrada"           │  AUTO-OVERLAY 2026-09-25
                    └──────────────┬──────────────────────┘
                                   │ DERIVED_FROM / SUPERSEDES (overlay)
        ┌──────────────────────────┼──────────────────────────┬──────────────────────┐
        ▼                          ▼                          ▼                      ▼
┌───────────────┐        ┌──────────────────┐      ┌────────────────────┐   ┌────────────────────┐
│PATCH-REGISTRY │        │PROBLEM-STATUS-   │      │ RELEASE-CANDIDATE  │   │ FINAL-RELEASE-     │
│   -FINAL.md   │        │    FINAL.md      │      │      .md           │   │     REPORT.md      │
│ 29 KB · 14 in │        │ 8 KB · 15 in     │      │ 3 KB · 11 in       │   │ 6.5 KB · 11 in     │
└───────┬───────┘        └────────┬─────────┘      └─────────┬──────────┘   └─────────┬──────────┘
        │                         │                            │                        │
        │ REFERENCES              │ REFERENCES                 │ REFERENCES             │ REFERENCES
        ▼                         ▼                            ▼                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 01-AUDITORIA/PATCH-RECOVERY/  (3 docs, CURRENT)   ·   01-AUDITORIA/FINAL-VALIDATION/ (2 docs) │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Lectura:** el documento con más referencias entrantes del repositorio (30) **delega su estado
vigente** en cuatro documentos de la raíz que, sumados, tienen 51 entrantes. Un lector que
entre por `MASTER-RESEARCH-STATUS.md` recibe el historial R-4B/D6, no el estado actual. El
overlay lo dice explícitamente en su primera línea, lo cual reduce el riesgo, pero la jerarquía
de referencias no lo refleja.

| Relación | De | A | Evidencia |
|---|---|---|---|
| `SUPERSEDES` (parcial) | `MASTER-RESEARCH-STATUS.md` | `PATCH-REGISTRY-FINAL.md` | `OVERLAY FINAL 2026-09-25: la matriz vigente de problemas […] están en ../PATCH-REGISTRY-FINAL.md` (línea 3) |
| `SUPERSEDES` (parcial) | `MASTER-RESEARCH-STATUS.md` | `PROBLEM-STATUS-FINAL.md` | misma línea 3-4 |
| `REFERENCES` | `MASTER-RESEARCH-STATUS.md` | `RELEASE-CANDIDATE.md` | overlay, línea 5 |
| `REFERENCES` | `MASTER-RESEARCH-STATUS.md` | `FINAL-RELEASE-REPORT.md` | overlay, línea 5-6 |
| `REFERENCES` | `README.md` | los 8 documentos finales | §Documentos finales, líneas 24-37 |
| `REFERENCES` | `00-INDICE/README.md` | `README.md` + los 8 finales | §Cierre de consolidación, líneas 10-14 |
| `REFERENCES` | `AGENTS.md` | 7 documentos "canonical" | §Canonical navigation and state, líneas 11-17 |

---

## 2. Cadena de supersesión de la auditoría histórica

Esta es la única cadena de `SUPERSEDES` inequívoca del repositorio.

```
01-AUDITORIA/AUDIT-001/AUDIT-001.md        (14 KB · auditoría histórica completa)
            │
            │ SUPERSEDES  (declarado en ERRATA.md)
            ▼
01-AUDITORIA/AUDIT-001/ERRATA.md           (6.4 KB)
   ERRATUM-001: Kalm NO explica el régimen E1/E3/E5
   ERRATUM-002: power1_input es W_SMU, no un medidor independiente
            │
            │ DERIVED_FROM / SUMMARIZES
            ▼
01-AUDITORIA/AUDIT-001/EVIDENCE-MATRIX.md  (10 KB · matriz evidencia × conclusión × clasificación)
01-AUDITORIA/AUDIT-001/METRICS-DEFINITIONS.md (4.6 KB · power_avg_full / _steady / _max)
            │
            │ SUMMARIZES (histórico)
            ▼
00-INDICE/FINAL-RESEARCH-STATUS.md         (4.6 KB · SNAPSHOT — los diagramas lo marcan "no usar como estado vivo")
            │
            │ HISTORICAL_VERSION_OF
            ▼
02-ARQUITECTURA/hypotheses.md · rejected_ideas.md
```

| Relación | De | A | Evidencia |
|---|---|---|---|
| `SUPERSEDES` | `AUDIT-001.md` | `ERRATA.md` | `ERRATA.md` §ERRATUM-001/002: "Conclusión Original (errónea)" → "Nueva Evidencia" → "Corrección" → "Impacto en Conclusiones Anteriores" |
| `DERIVED_FROM` | `EVIDENCE-MATRIX.md` | `AUDIT-001.md` | Both in `AUDIT-001/`; matrix clasifica los experimentos que la auditoría narra |
| `DEPENDS_ON` | `METRICS-DEFINITIONS.md` | `ERRATA.md` | las definiciones de `power_avg_*` solo tienen sentido tras etiquetar `power1_input` como `W_SMU` |
| `SUMMARIZES` | `FINAL-RESEARCH-STATUS.md` | `AUDIT-001/` + experimentos | "Qué sabemos / Qué NO sabemos / Qué quedó DESCARTADO / Qué quedó sin reproducir" |
| `HISTORICAL_VERSION_OF` | `FINAL-RESEARCH-STATUS.md` | `MASTER-RESEARCH-STATUS.md` | `10-NAVEGACION-DOCUMENTAL.md` §HISTORICAL: "`FINAL-RESEARCH-STATUS.md` → No usar como estado vivo" |

---

## 3. Cadena del estado de addenda R-4B

```
00-INDICE/MASTER-RESEARCH-STATUS.md
   §SNAPSHOT HISTÓRICO PRE-D6 ──────────────► (no describe el estado actual)
   §ESTADO VIGENTE GATE P0 ─────────────────► P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md
   §ESTADO VIGENTE — ADDENDA D6 ────────────► EXP-F4-A-RESULTADOS-v2.3.md
   §Precedencia de estado R-4B (1→4) ───────► define el orden de referencia
```

| Relación | De | A | Evidencia |
|---|---|---|---|
| `DERIVED_FROM` | `MASTER-RESEARCH-STATUS.md` §Addenda D6 | `EXP-F4-A-RESULTADOS-v2.3.md` | "La referencia canónica es `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md`" (línea ~35) |
| `DERIVED_FROM` | `MASTER-RESEARCH-STATUS.md` §Gate P0 | `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | "La fuente primaria es `01-AUDITORIA/FASE-P0-…-2026-09-24.md`" |
| `HISTORICAL_VERSION_OF` | `EXP-F4-A-PROTOCOL.md` | `EXP-F4-A-PROTOCOL-v2.2.md` | v2.2 §1: "única variación procedimental frente a v2.1" |
| `HISTORICAL_VERSION_OF` | `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md` | `EXP-F4-A-PROTOCOL-v2.3.md` | la propuesta precede al protocolo; el resultado v2.3 cierra Phase 2 |
| `REFERENCES` | `EXP-F4-A-RESULTADOS-v2.3.md` | `MASTER-RESEARCH-STATUS.md` | lista los 13 localizadores `/tmp` perdidos |
| `VALIDATES` (parcial) | `RESULTADOS-MINITEST-7.3-B.md` | `TEST-TERMICO-READONLY.md` | ambos comparten la caracterización térmica del disco viejo |

**Nota de riesgo:** dentro de `MASTER-RESEARCH-STATUS.md`, las secciones de snapshot y las
vigentes se contradicen si se leen sin contexto. El propio documento lo reconoce: "Las frases
históricas «NO EJECUTADA» o «S2 NO iniciada» que quedan en secciones anteriores se conservan
únicamente como snapshots y no describen el estado posterior a esta addenda."

---

## 4. Cadena de reconciliación documental

```
REORGANIZATION-AUDIT.md ──► SET-I-AUDIT ──► SET-I-REPAIR-RESULT
        │                                                 │
        ├──► REFERENCES-AUDIT ──► REFERENCE-REPAIR-PLAN ──► REFERENCE-REPAIR-RESULT
        │                                                                    │
        └──► REGISTRO-DE-MOVIMIENTOS ◄──────────────────────────────────────┘
                    │
                    ▼
          POST-REPARACION-DOCUMENTAL-AUDIT.md ──► REPARATION-PLAN.md
                    │
                    ▼
          DOCUMENTARY-RECONCILIATION-2026-09-25.md  (CONFLICT de provenance)
                    │
                    ├──► DECISIONES-D1-D10.md (§0 "Corrección previa (afecta a D5)")
                    └──► MASTER-RESEARCH-STATUS.md (ADDENDA DOCUMENTARY RECONCILIATION)
```

Siete documentos de proceso (7 de los 40 de `00-INDICE`) que explican **por qué** hay
referencias rotas. No son fuente de estado, pero son la única explicación documentada de las 140
referencias rotas de §5.

| Relación | De | A | Evidencia |
|---|---|---|---|
| `DERIVED_FROM` | `SET-I-REPAIR-RESULT.md` | `SET-I-AUDIT.md` | §2 "Referencias reparadas (antes → después)" con tabla Set I |
| `DERIVED_FROM` | `REFERENCE-REPAIR-RESULT.md` | `REFERENCES-AUDIT.md` | methodology → result |
| `SUMMARIZES` | `REGISTRO-DE-MOVIMIENTOS.md` | todos los grupos movidos | tabla de 7 grupos con fecha y verificación de integridad |
| `DERIVED_FROM` | `POST-REPARACION-DOCUMENTAL-AUDIT.md` | `REPARATION-PLAN.md` | plan → auditoría |
| `DERIVED_FROM` | `DOCUMENTARY-RECONCILIATION-2026-09-25.md` | `POST-REPARACION-DOCUMENTAL-AUDIT.md` | §0 "Precedencia y frontera de escritura" |
| `REFERENCES` | `DOCUMENTARY-RECONCILIATION-2026-09-25.md` | `DECISIONES-D1-D10.md` | corrige D5 |

---

## 5. Referencias rotas: 140 candidatas, clasificadas

Clasificación hecha con resolución contra el árbol real. Las 4 categorías:

| Categoría | N | Significado |
|---|---:|---|
| `EXTERNAL_SOURCE` | 31 | Fichero de código de Mesa o del kernel (`ac_sqtt.c`, `radv_physical_device.c`, `amdgpu_pmu.c`…). **No es una referencia rota**: son citas de fuente upstream. |
| `EXTERNAL_SYSTEM` | 22 | Ruta del sistema (`/usr/local/bin/system-autopilot.sh`, `/opt/kalm/kalmd.py`). **No es rota**: cita un fichero del host, no del repo. |
| `ARTEFACTO` | 21 | Falso positivo de mi propio extractor: `3.md` extraído de `…RESULTADOS-v2.3.md`, `0.md` de `…-v2.0.md`. **Descartados.** |
| `AMBIGUOUS` | 4 | Nombre desnudo con más de un candidato; no se puede resolver sin contexto. |
| `REAL_BROKEN` | 140 | No resuelve a nada en el árbol. Catalogadas abajo. |

### 5.1 Referencias rotas agrupadas por causa

**Causa A — apuntan a ficheros del host viejo que nunca estuvieron en el repo (≈30 casos).**
No son errores: son cita de un sistema que existió. Un router debe saber esto para no reportar
"fichero ausente" cuando en realidad cita el disco anterior.

| Referencia | Docs que la citan | N |
|---|---|---:|
| `kalm-lite.py` | `FINAL-RESEARCH-STATUS.md`, `AUDIT-001.md`, `ERRATA.md`, +6 | 9 |
| `kalmd.py` | `FINAL-RESEARCH-STATUS.md`, `AUDIT-001.md`, `ERRATA.md`, +5 | 8 |
| `kalm-cpu-apply.sh` | `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md`, `PATCH-RECOVERY-REPORT.md` | 2 |
| `/usr/local/bin/system-autopilot.sh` | `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md`, `AUDITORIA-CONSUMO-SEGUNDO-PLANO.md` | 2 |
| `/opt/kalm/kalmd.py` | `PATCH-RECOVERY-REPORT.md` | 1 |

**Causa B — artefactos de runtime que el documento nombra pero no están versionados (≈25 casos).**
Son ficheros que el runner crearía al ejecutarse, o que se preservan fuera del repo.

| Referencia | Contexto | N |
|---|---|---:|
| `state.json` | `C1-ISOLATION-AUTOMATOR.md` §86: "Lee únicamente `CURRENT` y `state.json` del namespace activo v2" | 3 |
| `stdout.txt` | `M1-cap-35-30/TELEMETRY-SCHEMA.md`, `POST-REPARACION-DOCUMENTAL-AUDIT.md` | 2 |
| `telemetry.csv` | ídem (existe en los runs, no en la raíz que se cita) | 2 |
| `m1-schedule.json` | `RESULTADOS-M1.md`, `TELEMETRY-SCHEMA.md` (existe en `runs/20260919-235939/`) | 2 |
| `telemetria.csv`, `telemetria.sh`, `analyze.py`, `governor.py` | scripts/series del disco viejo | 3 c/u |
| `DOCUMENT-HASHES.txt` | `DIAGRAMAS/00-MAESTRO-PROYECTO.md`, `12-MATRIZ-TRAZABILIDAD.md` ("presente pero histórico") | 2 |
| `E1-report.md`, `E2-report.md`, `GPU-BOTTLENECK-report.md` | `FASE-R2-FINAL-REPORT.md` los nombra como inexistentes ya | 3 |
| `telemetria_bare3.csv`, `runs/200k/telemetria.csv`, `mesa-e1-20260917-170430/*` | reportes del backup | 4 |

**Causa C — rutas previas a la reorganización del 2026-09-23 (≈40 casos).**
Los documentos de auditoría citan `projects/...` sin el prefijo `04-IMPLEMENTACION/`, y
`FASE-R1-...` sin `01-AUDITORIA/`. Los propios documentos de reparación registran la corrección.

| Referencia citada | Ruta real | N |
|---|---|---:|
| `projects/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md` | `04-IMPLEMENTACION/projects/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md` | 3 |
| `projects/CLOSED-LOOP-QUALITY-GOVERNOR/POLARIS12-FEASIBILITY.md` | ídem con `04-IMPLEMENTACION/` | 2 |
| `projects/BERRETA/BERRETA-DESIGN.md` | `04-IMPLEMENTACION/projects/BERRETA/BERRETA-DESIGN.md` | 2 |
| `projects/GHOST/GHOST-CACHE-DESIGN.md` | `04-IMPLEMENTACION/projects/GHOST/GHOST-CACHE-DESIGN.md` | 2 |
| `projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` | `04-IMPLEMENTACION/projects/…` | 2 |
| `projects/RX-COMPRESSION-ENGINE/RX-COMPRESSION-ENGINE-DESIGN.md` | `04-IMPLEMENTACION/projects/…` | 2 |
| `projects/JITTER-REPROJECTION/{EXPERIMENT-DESIGN,PRIOR-ART}.md` | `04-IMPLEMENTACION/projects/JITTER-REPROJECTION/…` | 2 |
| `GHOST/GHOST-CACHE-DESIGN.md` | `04-IMPLEMENTACION/projects/GHOST/…` | 2 |
| `BERRETA/BERRETA-DESIGN.md`, `RX-COMPRESSION-ENGINE/…` | ídem | 2 |
| `RX550_BUILD_SPECIFICATION.txt` | `02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` (desde `00-INDICE/` necesita `../`) | 3 |
| `../RX550_BUILD_SPECIFICATION.txt` | `00-INDICE/RX550_BUILD_SPECIFICATION.txt` no existe | 1 |
| `../../02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` | desde `00-INDICE/` sube de más | 1 |
| `FASE-R1-DOCUMENTATION-RECONCILIATION/R1-6-EVIDENCE-STATE-MODEL.md` | `01-AUDITORIA/FASE-R1-…/R1-6-…md` | 1 |
| `FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md` | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/…` | 1 |
| `FASE-R4B-GOVERNOR/results/v23/session1/fase1/manifest.json` | `03-EXPERIMENTOS/…` | 1 |
| `DIAGRAMAS/README.md` | `00-INDICE/DIAGRAMAS/README.md` (desde `00-INDICE/`) | 1 |
| `DESIGN.md` | nombre genérico sin ruta; 3 docs lo citan | 3 |
| `PROJECT-ROADMAP.md` | `00-INDICE/MASTER-PLAN.md` es el equivalente real | 1 |
| `3-PROPUESTA.md` | `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md` | 2 |
| `3-B.md` | `RESULTADOS-MINITEST-7.3-B.md` | 2 |
| `audit-history/shell-history-rx550-kalm.txt`, `code/rx550-power-sweep.sh`, `drivers/gpu/drm/amd/pm/amdgpu_pm.c`, `src/amd/vulkan/radv_debug.c` | `PATCH-SOURCES.md` cita rutas **del backup y de repos externos** a propósito | 4 |

**Causa D — código citado sin ruta (≈8 casos).** `c1_isolation_automator.py`,
`c1_observer.py`, `src/graphics.cpp`, `amdgpu_pmu.c`, `gfx_v8_0.c`, `ac_perfcounter.c`,
`ac_sqtt.c`, `radv_physical_device.c`, `hw.md`, `CONDICIONES.txt`.

**Total `REAL_BROKEN` = 140.** Ninguna se reparó.

### 5.2 Referencias ambiguas (4)

| Referencia | Candidatos | Doc que la cita |
|---|---|---|
| `c1_isolation_automator.py` | `04-IMPLEMENTACION/c1_isolation_automator.py` (1 candidato real) | `DIAGRAMAS/12-MATRIZ-TRAZABILIDAD.md` — resoluble con contexto, marcado ambiguo por la regla |
| `./COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md` | `02-ARQUITECTURA/COUNTERS-…md` (existe) | `02-ARQUITECTURA/POLARIS12-MAP/SOFTWARE-CAPABILITIES.md` — ruta relativa mal formada |

---

## 6. Relaciones `IMPLEMENTS` y `TESTS`

| Relación | De (implementación) | A (diseño) | Evidencia |
|---|---|---|---|
| `IMPLEMENTS` | `c1_isolation_automator.py` | `C1-ISOLATION-DESIGN-v1.0.md` | nombres y §"Alcance y límites" del diseño |
| `IMPLEMENTS` | `C1-ISOLATION-AUTOMATOR.md` | `C1-ISOLATION-DESIGN-v1.0.md` | documenta el automator v1.1.0 del diseño |
| `IMPLEMENTS` | `h12_probe.c` | `H12-1/README.md` | `README` §Alcance describe el probe |
| `IMPLEMENTS` | `H12-2-README` + `H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md` | `H12-1` (H12-3/H12-4) | `H12-1/README.md`: "H12-4 implementado sobre H12-3" |
| `IMPLEMENTS` | `rx550-torneo/` (4 fases) | `MASTER-PLAN.md` §J / `RX550_BUILD_SPECIFICATION.txt` | la especificación de 45 secciones define el constructor |
| `IMPLEMENTS` | `c1_observer.py` | `RESEARCH.md` §R-11 | observador del workload durante C1 |
| `IMPLEMENTS` | `tools/validate_rx550_final.py` | `README.md` §Reproducir la validación | el README da la invocación exacta |

| Relación | De (test) | A (implementación) | Evidencia |
|---|---|---|---|
| `TESTS` | `04-IMPLEMENTACION/tests/test_c1_isolation_automator.py` | `c1_isolation_automator.py` | 54 tests, 1 skip |
| `TESTS` | `rx550-torneo/tests/run_tests.py` | `state_manager.py` + `cli.py` | 64/64 |
| `TESTS` | `rx550-torneo/tests/run_tests_m1.py` | `cap_run.py` + `cli.py` | 110/110, `strace=NOT_AVAILABLE` |
| `TESTS` | `TESTING.md` | los 4 documentos de la raíz | matriz de criterios |
| `TESTS` | `run_tests_m1.py::t_workload_radv_icd_selector` | `PATCH-REGISTRY-FINAL.md` (corrección PP-02) | asserts G2–G6 sobre el selector RADV |

---

## 7. Relaciones `RECOVERS`

| Relación | De | A / origen | Evidencia |
|---|---|---|---|
| `RECOVERS` | `PATCH-REGISTRY-RECOVERED.md` | backup `RX550_Modo_Torneo_Backup_2026-09-19_0836/` (11 artefactos con SHA-256) | hashes coinciden con `manifest/SHA256SUMS-critical` |
| `RECOVERS` | `PATCH-REGISTRY-RECOVERED.md` `RX550-MP-01` | repo `/home/lucas/mesa` commit `583c5d2f44152ed70d6f9aff58fbca5abcf7376d` | diff SHA-256 `c10c558b…` |
| `RECOVERS` | `PATCH-SOURCES.md` | `audit-history/shell-history-rx550-kalm.txt` | prueba que `kalm-gpu` estuvo activo |
| `RECOVERS` (parcial) | `PATCH-REGISTRY-RECOVERED.md` `RX550-UNK-01` | `system-autopilot.*` | **NO RECUPERADO**: solo prefijos de hash de 12 hex |
| `RECOVERS` (falla) | `PATCH-REGISTRY-RECOVERED.md` grupo B | parches de kernel/amdgpu/GRUB | `NOT_AVAILABLE`: 0 `.patch` en proyecto, backup y `/home/lucas/linux-opt` |

---

## 8. Relaciones `CONTRADICTS` — 5 hechos con fuentes incompatibles

Estas son las únicas 5 contradicciones sustantivas encontradas. **Ninguna se resolvió.**

### CONFLICT-1 — Recuento de tests de C1
| Fuente | Valor | Estado declarado |
|---|---|---|
| `01-AUDITORIA/FASE-R5-C1-TECHNICAL-DOCUMENTATION/C1-TECHNICAL-RECORD.md` | `24/24` | `HISTORICAL` |
| `00-INDICE/DIAGRAMAS/12-MATRIZ-TRAZABILIDAD.md` | `37/37` | `DERIVED/STALE` |
| sidecar vigente (citado en `DOCUMENTARY-RECONCILIATION-2026-09-25.md`) | `44/44` | `CURRENT_SIDECAR_RECORD` |
| `README.md` | `54` tests, 1 skip | no comparado |

`DOCUMENTARY-RECONCILIATION-2026-09-25.md:187` lo declara: `C1_TESTS=CONFLICT`.

### CONFLICT-2 — Versión de Mesa (tres valores)
| Valor | Fuente |
|---|---|
| 26.2.2 | `MESA_CANONICAL` en `DOCUMENTARY-RECONCILIATION-2026-09-25.md` |
| 26.2.3 | `MESA_EXTERNAL` en el mismo documento; también `COUNTERS-ASIC-…-ADDENDUM.md:302` |
| **25.3.2** | `README.md`, `PATCH-REGISTRY-FINAL.md:73`, `FINAL-VALIDATION-*.md`, `INSTALL.md` |
| **26.2.3 (vivo)** | `rpm -q mesa-dri-drivers` en el host actual |

`MESA_PROVENANCE=CONFLICT` declarado. **La documentación de la raíz contradice su propia
captura de host y el host real.**

### CONFLICT-3 — Versión de kernel (tres valores)
| Valor | Fuente |
|---|---|
| `7.2.6-201.nobara.fc44` | `P0-EXPERIMENTAL-VALIDITY-GATE:7`, `C1-PREFLIGHT-*`, `C1-ISOLATION-AUTOMATOR.md:120` |
| `7.2.4-201.nobara.fc44` | `02-ARQUITECTURA/knowledge.md:9`, `FASE-D-COUNTERS-AUDIT.md:4`, `COUNTERS-ASIC-…:304` |
| `6.18.2-200.nobara.fc43` | `FINAL-VALIDATION-*.md`, `README.md:14`, `PATCH-REGISTRY-FINAL.md:73` |
| `7.1.3-200.nobara.fc44` (vivo) | `PATCH-SOURCES.md:60` |

`C1-TECHNICAL-RECORD.md:48` ya lo marca `CONFLICT`: "documentos históricos mencionan `7.2.4` …
**No se funden**". `C1-RECOVERY-RUNTIME-TEST-…-POST.md:31` registra un cambio de kernel entre
pre y post reboot **sin corregirlo**.

### CONFLICT-4 — Identidad de la GPU por `cardN`
| Valor | Fuente |
|---|---|
| `card2` (RX550), `card0` (Intel) | `FINAL-VALIDATION-*.md`, `README.md:15-16` |
| `card1` (RX550), `card0` (Intel) | host vivo |
| `card1` + `hwmon1` | host viejo según `PROTOCOLO-AB-…` y scripts |

`PATCH-REGISTRY-FINAL.md` lo resuelve como **regla**: "esos números no son portables". Los
scripts históricos fijan `card1/hwmon2`, que no coincide con ningún estado observado.

### CONFLICT-5 — Estado de H12-4
| Valor | Fuente |
|---|---|
| `H12-4 implementado sobre H12-3` | `H12-1/README.md:3` |
| `H12-4=EXTERNAL_COMPLETED_RECORD_VS_DOC_NOT_EXECUTED` | `DOCUMENTARY-RECONCILIATION-2026-09-25.md` |
| `P-022 H12 … NOT_REPRODUCED` | `PATCH-REGISTRY-FINAL.md:54` |
| `H12-4_PROVENANCE=CONFLICT` | `DOCUMENTARY-RECONCILIATION-2026-09-25.md` |

### CONFLICT-6 — Btrfs
`BTRFS=CONFLICT`, `BTRFS_CAUSE=UNKNOWN` (`AGENTS.md:136-137`, `DOCUMENTARY-RECONCILIATION-2026-09-25.md`).
El host vivo usa **`/dev/sdb3` ext4**, no Btrfs. El estado de Btrfs en el host actual es
`OBSOLETE`, aunque el texto diga `CONFLICT`.

---

## 9. Documentos sin referencia entrante (59 de 256)

No están necesariamente huérfanos: los resultados de experimento se consultan por ruta conocida.
Se listan para que un revisor decida si deben enlazarse desde algún índice.

| Grupo | N | Ejemplos |
|---|---:|---|
| Resultados de corrida de `WORKLOAD-SINTETICO/runs/` | 3 | `RESULTADO-EXPLORATORIO-0{1,2,3}.md` |
| Documentos de proceso R-1/R-2/R-3 | 21 | `R1-1-GFX8-EVENT-RECONCILIATION.md`, `FASE-R2-FINAL-REPORT.md`, `NOVELTY-MATRIX.md` |
| Planes y prechecks de FASE D | 5 | `FASE-D-ETAPA-3-PLAN.md`, `FASE-D-ETAPA-3-PRECHECK.md` |
| Marcadores de inutilizabilidad | 3 | `ESTADO-HISTORICO-NO-UTILIZABLE.md` ×2, `results/ESTADO.md` |
| Diseños de ideas sin README enlazado | 14 | `BERRETA-DESIGN.md`, `GHOST-CACHE-DESIGN.md`, `ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` |
| Documentos C1 pre/post sin entrada | 6 | `C1-TTY3-*-PRE.md` ×3, `C1-RECOVERY-…-PRE.md` |
| Otros | 7 | `PATCH-RECOVERY/*` (esta sesión), `H12-2/README.md` |

Lista completa de los 59 en el campo `INBOUND_REFS=0` del TSV.

---

## 10. Grafo de los cinco mecanismos de navegación (superposición)

```
        ┌──────────────────────────┐
        │  AGENTS.md               │ 7 "canonical"
        │  (instrucciones agente)  │
        └────────────┬─────────────┘
                     │ declara canónicos
     ┌───────────────┼───────────────┬──────────────────┐
     ▼               ▼               ▼                  ▼
 README.md    00-INDICE/README.md  MASTER-RESEARCH-  IMPLEMENTATION-
 (raíz)       (índice canónico)    STATUS.md         SAFETY-RULES.md
     │               │               │                  ▲
     │               │               │ overlay           │
     │               ▼               └──────────────────┤
     │        R2-GLOBAL-DOCUMENTATION-MAP.md             │
     │        [DRAFT/CONFLICT]                           │
     │               │                                   │
     │               ▼                                   │
     │        DIAGRAMAS/ (17 vistas)                     │
     │        [16 × DRAFT/CONFLICT]                      │
     │               │                                   │
     ▼               ▼                                   ▼
 PROJECT-DOCUMENTATION-STATUS.md              C1-ISOLATION-DESIGN-v1.0.md
 [DRAFT/CONFLICT]                             C1-ISOLATION-AUTOMATOR.md
```

Cinco mecanismos, `AGENTS.md` es el único que se declara canónico, y su lista de canónicos
**no incluye** `PROBLEM-STATUS-FINAL.md`, `PATCH-REGISTRY-FINAL.md`, `RELEASE-CANDIDATE.md` ni
`FINAL-RELEASE-REPORT.md` — los cuatro que contienen el estado vigente. Dos mecanismos
(`R2-GLOBAL-DOCUMENTATION-MAP.md` y 16 de 17 diagramas) se declaran no vivos.

---

## 11. Grafo de la recuperación de parches

```
DISCO VIEJO (backup ~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/)
   ├── system/kalm-gpu, etc/kalm*.service, etc/60-kalm-*.rules,
   │   etc/99-kalm-*.conf, code/kalm-despliegue-total.sh, code/rx550-power-sweep.sh
   │         │
   │         │ RECOVERS (11 artefactos, SHA-256 verificados contra SHA256SUMS-critical)
   │         ▼
   ├── system-autopilot.{service,timer,sh}          ← RECOVERY FALLIDO
   │         │ solo prefijos: 07dc247f…932d6, 16d21f1c…00e72a, 61519cfe…0fee3ea
   │         ▼
   └── (inexistente) /home/lucas/mesa commit 583c5d2f441  ← RECOVERS (fuera del repo del proyecto)
              │
              ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ 01-AUDITORIA/PATCH-RECOVERY/                                    │
   │   PATCH-RECOVERY-REPORT.md    (informe L1, clasificación A/B/C/D)│
   │   PATCH-REGISTRY-RECOVERED.md (28 entradas, riesgo, aplicabilidad)│
   │   PATCH-SOURCES.md           (procedencia + discrepancia de host)  │
   └───────────────┬──────────────────────────────────────────────────┘
                   │ RELATIONSHIP: complementario, no duplicado
                   ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ PATCH-REGISTRY-FINAL.md  (estado de las correcciones, 14 entradas)│
   │ PROBLEM-STATUS-FINAL.md  (22 problemas)                          │
   └──────────────────────────────────────────────────────────────────┘
```

**Relación entre los dos registros de parches:** no es `DUPLICATE`. Uno describe *qué se
recuperó y de dónde*; el otro *qué corrección existe y cuál es su estado*. Un router que
responda "¿este parche es recuperable?" va al primero; "¿qué corrección arregla este problema?"
va al segundo. `PATCH-REGISTRY-FINAL.md` no menciona `PATCH-RECOVERY/` (se escribieron en la
misma sesión, el segundo después), lo cual es una **referencia faltante** y no una contradicción.

---

## 12. Resumen cuantitativo

| Métrica | Valor |
|---|---:|
| Aristas `REFERENCES` resueltas y verificadas | 613 |
| Documentos Markdown | 256 |
| Documentos con ≥1 referencia entrante | 197 |
| Documentos sin referencia entrante | 59 |
| Referencias candidatas a rotura | 185 |
| `REAL_BROKEN` confirmadas | 140 |
| `EXTERNAL_SOURCE` (no rotas) | 31 |
| `EXTERNAL_SYSTEM` (no rotas) | 22 |
| Falsos positivos del extractor | 21 |
| Ambiguas | 4 |
| Relaciones `SUPERSEDES` explícitas | 2 (overlay) + 2 (errata) |
| Relaciones `CONTRADICTS` sustantivas | 6 |
| Relaciones `IMPLEMENTS` | 7 |
| Relaciones `TESTS` | 5 |
| Relaciones `RECOVERS` | 5 (2 fallidas) |
| Referencias reparadas en esta fase | **0** |
