# PLAN DE REPARACIÓN DOCUMENTAL — RX550-INVESTIGACION

**Fecha**: 2026-09-23 · **Estado original**: **PLANIFICADO — NINGUNA REPARACIÓN EJECUTADA**
**Modo original de este documento**: READ-ONLY. No se modificó ningún archivo del proyecto en la fase de planificación.
**Decisiones cerradas**: D1–D10 (ver `01-AUDITORIA/DECISIONES-D1-D10.md`).

> **SNAPSHOT HISTÓRICO (reconciliación 2026-09-24):** las secciones de diagnóstico
> anteriores a la reconciliación conservan conflictos y opciones pasadas. Para el estado
> vigente prevalecen `MASTER-RESEARCH-STATUS.md`, las addendas D6 y los documentos canónicos.
**Único fichero creado en esta fase**: este plan. **No sobrescribe nada** (no existía).

> **ADDENDA DE EJECUCIÓN (2026-09-23):** la autorización explícita posterior permite
> ejecutar el plan. Las secciones originales anteriores se conservan como especificación
> histórica; el estado de ejecución y las desviaciones se registran al final de este
> documento. No se ha realizado ningún commit (D10).

## Decisiones adoptadas que gobiernan este plan

| Decisión | Acuerdo que se aplica |
|---|---|
| **D1** | `00-INDICE/README.md` = **índice canónico** de la estructura ACTUAL. Actualizar 5 rutas `experiments/` + las 6 referencias a ficheros ahora en `02-ARQUITECTURA/`. Distinguir índice canónico de referencias históricas. No eliminar información histórica necesaria |
| **D2** | `R2-GLOBAL-DOCUMENTATION-MAP.md` = **mapa de navegación DRAFT/CONFLICT**, no fuente experimental. Reparar **17 de 18** referencias; mantener **1** histórica (el backup). Sin sustitución global ciega. FASE-R2: 14 diseños → `04-IMPLEMENTACION/`, mapa → `00-INDICE/`. La raíz antigua vacía **puede permanecer** como raíz histórica |
| **D3** | Separar **4 conceptos**: descargado en repo / instalación externa / ejecución histórica / elegibilidad. GravityMark **HISTÓRICO NO DISCRIMINATIVO**, Superposition **INCONCLUSIVE**, Heaven/Valley **SIN RESULTADO**. No afirmar `VALID` global. |
| **D4** | El mapa es una vista de navegación `DRAFT/CONFLICT`; la descripción de `MASTER-PLAN.md:781` refleja los prefijos actuales y conserva el valor histórico |
| **D5** | Los 3 ficheros (FASE-E, FASE-F, SYNTHETIC-WORKLOAD-DESIGN) tienen correspondencia 1:1 con `04-IMPLEMENTACION/`. **No modificar contenido ni hashes** |
| **D6** | R-4B: S1 v2.3 **EJECUTADA/COMPLETADA**; S2 **INICIADA/PARADA D**; causa no verificada; veredicto global **INCONCLUSO/INCONCLUSIVE**. No borrar historia, no validar S2, no elevar a SUPPORTED |
| **D7** | Los 13 artefactos `/tmp` quedan **PERDIDOS / NO VERIFICABLES**. No reconstruir, no inferir. `gpa311/` = PARCIALMENTE RECUPERABLE (solo extracto R0-1). Telemetría en disco = evidencia independiente |
| **D8** | Set H **PROTEGIDO**: no modificar scripts, hashes, contenido ni mtimes. NO-GO = estado de ejecución, no pérdida de integridad |
| **D9** | Localizadores `/tmp` no existentes → **HISTÓRICOS / NO VERIFICABLES**. Sin rutas inventadas |
| **Power sweeps** | `132309` = histórico **NO UTILIZABLE** (datos Intel HD 4600). `140527` = histórico RX550 **NO UTILIZABLE CUANTITATIVAMENTE** (columnas desalineadas). No borrar los 388 ficheros |
| **D10** | **Sin commit** hasta cerrar decisiones y ejecutar reparaciones. Al final, **un commit de reparación documental coherente** |

---

# 1. Los 14 archivos que requieren reparación

| # | Archivo | Categoría | Cambio previsto | Decisión que lo autoriza |
|---|---|---|---|---|
| F1 | `00-INDICE/README.md` | A/B | Índice canónico: 11 rutas (5 `experiments/` + 6 ficheros movidos) | D1 |
| F2 | `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` | A/B | Mapa vivo: 17 de 18 referencias | D2 |
| F3 | `00-INDICE/MASTER-PLAN.md` | B/D | Línea 781 = descripción del mapa vivo | D4 |
| F4 | `00-INDICE/MASTER-RESEARCH-STATUS.md` | D | Estado R-4B v2.3 (addenda) + `rx550-torneo/:371` | D6 |
| F5 | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | B | Localizadores abreviados (D) | D1/D2 |
| F6 | `README.md` (raíz) | B/D | Narrativa de reorganización obsoleta | D1 |
| F7 | `01-AUDITORIA/FASE-R1…/R1-5-DOCUMENTATION-STATUS.md` | A | Alias R0 inexistentes → 4 nombres actuales | — |
| F8 | `01-AUDITORIA/FASE-R2…/R2-HISTORICAL-EXPERIMENT-INVENTORY.md` | A | Typo `/home/lucas/RX550_Modo_Torneo_Backup…` → insertar `/Escritorio` | — |
| F9 | `03-EXPERIMENTOS/M1-cap-35-30/run-m1.sh` | B | `$HERE/../../rx550-torneo` → ruta real | — |
| F10 | `03-EXPERIMENTOS/fase-b…/driver.sh` + `ep05…/scripts/{ab-e5,ab-e5-vk,env-check}.sh` | B | Localizadores `/tmp` → marcar históricos | D9 |
| F11 | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md` | D | 13 artefactos `/tmp` no verificables | D7 |
| F12 | `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/RESULTADOS-MINITEST-7.3-B.md` | B | `t90≈221 s` → extrapolación no lineal | D6 (contexto) |
| F13 | `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md` | A/D | 2 rutas rotas + 3 conceptos + 4 estados | D3 |
| F14 | `04-IMPLEMENTACION/FASE-G-MEMORY-VRAM-GTT-DESIGN.md` | A | `projects/GHOST/…` → `04-IMPLEMENTACION/projects/GHOST/…` | — |

**Además (no contados en los 14, por ser mechanical de bajo riesgo)**: 11 cabeceras de `04-IMPLEMENTACION/projects/*/` con prefijo `projects/` (ver §3.2), y `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/PRIOR-ART.md:99`.

---

# 2. Las 12 referencias rotas — detalle exacto

| # | Archivo | Línea/sección | Referencia actual | Destino correcto | Cambio propuesto | Tipo |
|---|---|---|---|---|---|---|
| R1 | `00-INDICE/README.md` | `:25` | `` `experiments/fase-a-discriminacion-20260919-114241/` `` | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/` | anteponer `03-EXPERIMENTOS/` | A |
| R2 | `00-INDICE/README.md` | `:26` | `` `experiments/fase-b-cap-probe-20260919-122038/` `` | `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/` | anteponer `03-EXPERIMENTOS/` | A |
| R3 | `00-INDICE/README.md` | `:27` | `` `experiments/ep06-soak-cap-20260919-205645/` `` | `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/` | anteponer `03-EXPERIMENTOS/` | A |
| R4 | `00-INDICE/README.md` | `:28` | `` `experiments/ep05-mesa-custom-20260919-212249/` `` | `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249/` | anteponer `03-EXPERIMENTOS/` | A |
| R5 | `00-INDICE/README.md` | `:29-30` | `` `experiments/M1-cap-35-30/` `` | `03-EXPERIMENTOS/M1-cap-35-30/` | anteponer `03-EXPERIMENTOS/` | A |
| R6 | `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md` | `:195` | `` `experiments/EXPLORATORIO-GravityMark/runs/RESULTADO-Superposition.md `` | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/RESULTADO-Superposition.md` | anteponer `03-EXPERIMENTOS/` | A |
| R7 | `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md` | `:197` | `` `experiments/EXPLORATORIO-GravityMark/runs/RESULTADO.md `` | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/RESULTADO.md` | anteponer `03-EXPERIMENTOS/` | A |
| R8 | `04-IMPLEMENTACION/FASE-G-MEMORY-VRAM-GTT-DESIGN.md` | `:7` | `` `projects/GHOST/GHOST-CACHE-DESIGN.md` `` | `04-IMPLEMENTACION/projects/GHOST/GHOST-CACHE-DESIGN.md` | anteponer `04-IMPLEMENTACION/` | A |
| R9 | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/PRIOR-ART.md` | `:99` | `projects/JITTER-REPROJECTION/PRIOR-ART.md` (en prosa, cita bibliográfica) | `04-IMPLEMENTACION/projects/JITTER-REPROJECTION/PRIOR-ART.md` | anteponer `04-IMPLEMENTACION/` | A |
| R10 | `01-AUDITORIA/FASE-R2…/R2-HISTORICAL-EXPERIMENT-INVENTORY.md` | `:54` | `/home/lucas/RX550_Modo_Torneo_Backup_2026-09-19_0836/experiments/` | `/home/lucas/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/experiments/` | insertar `/Escritorio` | A |
| R11 | `03-EXPERIMENTOS/M1-cap-35-30/run-m1.sh` | `:6,10,13,16` | `ROOT="$(cd "$HERE/../../rx550-torneo" …)"` (resuelve a `<raíz>/rx550-torneo`, inexistente) | `<raíz>/04-IMPLEMENTACION/rx550-torneo` | cambiar `../../rx550-torneo` → `../../04-IMPLEMENTACION/rx550-torneo` | B |
| R12 | `03-EXPERIMENTOS/fase-b…/driver.sh:3` + `ep05…/scripts/{ab-e5,ab-e5-vk,env-check}.sh:3` | `:3` | `/tmp/opencode/{fase_b_base,ep05_base}.txt` | **sin destino actual** | **NO sustituir**: marcar `HISTÓRICO / NO VERIFICABLE` (D9) | B |

**R11 y R12 requieren tratamiento distinto**: R11 es un bug de ruta en un script **no ejecutado**; R12 es un artefacto volátil **no reconstruible**. R11 puede corregirse mecánicamente; R12 solo se puede **anotar**.

---

# 3. Las ~30 referencias ambiguas (D)

## 3.1 Las que se resuelven mecánicamente (no requieren decisión)

| Archivo | Referencia | Por qué es ambigua | Resolución propuesta |
|---|---|---|---|
| `MASTER-RESEARCH-STATUS.md:371` | `` `rx550-torneo/` `` | sin `04-IMPLEMENTACION/` | anteponer `04-IMPLEMENTACION/` (D2 coherente) |
| `PROJECT-DOCUMENTATION-STATUS.md:60` | `` `rx550-torneo/README-*` `` | ídem | prefijo completo |
| `MASTER-PLAN.md:5` | `PROJECT-ROADMAP.md` | fichero que no existe | ver §4 (futura) |
| 11 cabeceras `04-IMPLEMENTACION/projects/*/` | `projects/BERRETA/…`, `projects/TBDR-IMR/…` etc. | prefijo `projects/` sin el directorio superior | anteponer `04-IMPLEMENTACION/` (cosmético) |

## 3.2 Las que requieren decisión humana adicional

| # | Archivo:línea | Referencia | Por qué es ambigua | Resolución propuesta | ¿Decisión humana? |
|---|---|---|---|---|---|
| A1 | `MASTER-PLAN.md:781` | `experiments/ A–D/R-0/R-1/sintético` (descripción de R-2.2) | descripción del mapa en pasado | actualizar a estructura actual (D4) | **Sí** (D4, depende de D2) |
| A2 | `PROJECT-DOCUMENTATION-STATUS.md:3,25,27-45,60,64` | “raíz del repositorio”, `fase-b…`, `ep05…`, `FASE-X-…DESIGN.md` | localizadores relativos sin directorio | prefijo o nota de contexto | **Sí** (dentro de D1) |
| A3 | `R2-GLOBAL-DOCUMENTATION-MAP.md:23,44,50-175` | 18 refs a raíz antigua | mapa pre-movimiento completo | reparar 17 / mantener 1 (D2) | **Sí** (D2) |
| A4 | `FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md:58` | `projects/... → NO toca` | metanota, no locator | **no tocar** (es una nota) | No |
| A5 | `IMPLEMENTATION-READINESS-AUDIT.md` (múltiples) | localizadores abreviados y temporales | auditoría congelada | **no tocar** (F) | No |
| A6 | `MASTER-PLAN.md:82,104`, `MASTER-RESEARCH-STATUS.md:50,388`, `PROJECT-DOCUMENTATION-STATUS.md:61` | `~/Escritorio/berchmark/instalados/` | externo deliberado, existe | dejar (externo) | No |
| A7 | `BENCHMARK-INVENTORY.md:3,27,120,186,190-202` | rutas externas de benchmarks, `/opt/mesa-26.2.2-rx550-haswell` | externos | dejar (D3: separar estado) | **Sí** (D3) |
| A8 | `RESULTADOS-MINITEST-7.3-B.md:163`, `EXP-F4-A-MINITEST-RAMP-GOV-PLAN.md:107` | `/tmp/opencode/analyze_minitest_ramp.py` | no archivado | marcar no verificable (D7/D9) | No (cubierto por D7) |
| A9 | `EXP-F4-A-RESULTADOS-v2.3.md:18,165-166` | `/tmp/opencode/micro12/…`, `marcar_ventanas.py` | no archivado | marcar no verificable (D7) | No (cubierto) |
| A10 | `FASE-D-ETAPA-3-PRECHECK.md:32,239` | `/tmp/opencode/rt_idle.csv` | no archivado | marcar no verificable (D9) | No |
| A11 | `MASTER-PLAN.md:89`, `BENCHMARK-INVENTORY.md:195` | `~/.Superposition/license` | requisito, no locator interno | dejar (no es ruta del repo) | No |
| A12 | `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md:323-324` | `/tmp/opencode/audit_p2_thermal.py`, `audit_power_win.py` | no archivados | marcar no verificable (D7) | No |
| A13 | `REGISTRO-DE-MOVIMIENTOS.md:9`, `REORGANIZATION-AUDIT.md` (tablas) | `RX550_Iterative_Research/…` | registro de movimiento | **no tocar** (bitácora, G) | No |
| A14 | `POST-REORGANIZATION-*.md`, `REGISTRO-DE-REPARACION-REFERENCIAS.md` | refs antiguas en los informes de reparación | bitácora de reparación | **no tocar** (F) | No |
| A15 | `M1-cap-35-30/runs/*/m1-schedule.json` | `run_dir` bajo raíz antigua | JSON congelado | **no tocar** (F) | No |
| A16 | `FASE-R4B-GOVERNOR/harness/build/**` | CMake/Ninja con raíz antigua | artefacto generado | **no tocar** (F) | No |
| A17 | `state_*.txt` | `lrwxrwxrwx … cardN` | texto de snapshot, no symlink | **no tocar** (F) | No |
| A18 | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/200k/times_200k.txt` | citado en resultado | ausente por timeout documentado | marcar no verificable | No |
| A19 | `FASE-R2-FINAL-REPORT.md`, `R3-MASTER-PLAN-INTEGRATION-PROPOSAL.md` | `experiments/`, `projects/` en contexto R-2/R-3 | docs de auditoría histórica | **no tocar** (G/F) | No |
| A20 | `MASTER-RESEARCH-STATUS.md:175` | `R2-GLOBAL-DOCUMENTATION-MAP.md` como entregable vivo | coherente tras D2 | sin cambio | No |
| A21 | `R2-GLOBAL-DOCUMENTATION-MAP.md:172-173` | backup como 4.ª capa | **referencia histórica válida** (D2: mantener 1) | **mantener** | No |
| A22 | `02-ARQUITECTURA/evidence.md:3,25`, `research_log.md:8` | backup y experimentos históricos | docs vivos que citan historia | anotar, no reescribir | **Sí** (D4-like) |
| A23 | `R1-1-GFX8-EVENT-RECONCILIATION.md:144`, `FASE-D-GFX8-EVENT-ID-AUDIT.md:22,28` | `RX550_Modo_Torneo_Backup_…` | backup externo, existe | dejar (G) | No |
| A24 | `FASE-R2-DOCUMENTATION/R2-GLOBAL-DOCUMENTATION-MAP.md` (ref. en `REGISTRO-DE-MOVIMIENTOS.md:9`) | 14 diseños + mapa movidos | ya registrado como completado | sin cambio | No |
| A25 | `MASTER-RESEARCH-STATUS.md:213,375,381,384`, `REGISTRO-DE-REPARACION-REFERENCIAS.md:100,147` | `R1-1..R1-15`, `F2-*`, `FUSION-01..` | placeholders / notación de conjunto | **no tocar** (no son rutas) | No |
| A26 | `POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md:121`, `SET-I-AUDIT.md:24,49` | `projects/I-*` | etiquetas internas, no directorios | **no tocar** (documentado) | No |
| A27 | `04-IMPLEMENTACION/rx550-torneo/README-FASE2.md:83`, `README-FASE3.md:144` | `~/Escritorio/RX550-INVESTIGACION/04-IMPLEMENTACION/rx550-torneo` | ya canónico | sin cambio | No |
| A28 | `FASE-R4B-GOVERNOR/run_all_v23.sh:85` | `$OMISSIONS.bak` | backup operativo, no ref obsoleta | sin cambio | No |
| A29 | `R2-HISTORICAL-EXPERIMENT-INVENTORY.md:19,30` | backup `RX550_Modo_Torneo_Backup_…` | histórico, existe | sin cambio (línea 54 sí se corrige) | No |
| A30 | `00-INDICE/README.md:31` | `~/Escritorio/RX550_Modo_Torneo_Backup_…` | histórico declarado | **mantener** (D1: no eliminar histórico) | No |

**Resumen §3:** de ~30 ambiguas, **3 requieren decisión humana adicional** (A1/D4, A2/D1, A3/D2, A7/D3) y el resto se resuelven mecánicamente, se dejan por ser externos/históricos, o están cubiertos por D7–D9.

---

# 4. Las 8 referencias futuras (E)

**Qué significa “futura”**: documentos o salidas **citados antes de existir**. No son errores de reparación: son tareas planificadas o placeholders. **No deben convertirse automáticamente en rutas actuales.**

| # | Referencia | Qué significa | Citada en | Tratamiento |
|---|---|---|---|---|
| E1 | `00-INDICE/FUENTES-FALTANTES.md` | documento a crear (inventario de UNKNOWN/fuentes) | `README.md:28`, `REORGANIZATION-AUDIT.md:156,260,294`, `POST-REORGANIZATION-*RESULT.md:171` | crear en fase de documentos nuevos (§6); **no** sustituir por nada existente |
| E2 | `IMPLEMENTATION-ROADMAP.md` | documento a crear (hoja de ruta de implementación) | `IMPLEMENTATION-READINESS-AUDIT.md:927-928`, `REORGANIZATION-AUDIT.md:257` | crear; ubicación a decidir (D: `04-IMPLEMENTACION/` o junto al audit) |
| E3 | `IMPLEMENTATION-SAFETY-RULES.md` | documento a crear (frontera de seguridad) | ídem | crear |
| E4 | `PROJECT-ROADMAP.md` | norte conceptual (no archivo) | `MASTER-PLAN.md:5` | **no crear** salvo decisión; el `MASTER-PLAN.md` ya cumple la función. Si se crea, es un documento nuevo (C) |
| E5 | `snapshot-gfx800-PRECHECK.txt` | salida de precheck FASE-D Etapa 3, no generada | `FASE-D-ETAPA-3-PRECHECK.md` | **no crear ni sustituir**; la Etapa 3 sigue abierta |
| E6 | `snapshot-gmc810-PRECHECK.txt` | ídem | ídem | ídem |
| E7 | `~/.Superposition/license` | requisito de una prueba futura (licencia Pro) | `MASTER-PLAN.md:89`, `BENCHMARK-INVENTORY.md:195`, `IMPLEMENTATION-READINESS-AUDIT.md:732`, `RESULTADO-Superposition.md:64-67` | **no crear**; Superposition se ejecutó en modo por defecto (INCONCLUSIVE). Requisito pendiente de licencia |
| E8 | “posible generación de `~/.Superposition/license`” | Misma causa que E7 | `RESULTADO-Superposition.md:64-67` | Se combina con E7 |

**Ninguna de las 8 se convierte en ruta actual por acción de este plan.**

---

# 5. Los localizadores `/tmp/opencode/` (13 verificados; el usuario comptait 11)

**Reconciliación de recuento**: la búsqueda global devuelve **13 localizadores únicos**. De ellos, **1** (`ep06_base.txt`) es leído por 2 scripts de **Set H** (protegido, F) y **2** (`f4a-s/`, `f4a-smoke/`) son el mismo requisito (preflight F-4A) citado en 2 líneas del mismo fichero. Dependiendo de si se cuentan por fichero o por línea, el total es 11–13. Se listan los **13 verificados**.

| # | Localizador | Estado | Referenciado en | Tratamiento (D7/D9) |
|---|---|---|---|---|
| T1 | `/tmp/opencode/micro12/vkmark30-telemetry.csv` | **PERDIDO** | `EXP-F4-A-RESULTADOS-v2.3.md:18,165` | marcar **NO VERIFICABLE**; no reconstruir (es la evidencia de la PARADA D) |
| T2 | `/tmp/opencode/marcar_ventanas.py` | **PERDIDO** | `EXP-F4-A-RESULTADOS-v2.3.md:166` | **NO VERIFICABLE**; no reconstruir |
| T3 | `/tmp/opencode/audit_p2_thermal.py` | **PERDIDO** | `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md:323` | **NO VERIFICABLE** |
| T4 | `/tmp/opencode/audit_power_win.py` | **PERDIDO** | `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md:324` | **NO VERIFICABLE** |
| T5 | `/tmp/opencode/analyze_minitest_ramp.py` | **PERDIDO** | `RESULTADOS-MINITEST-7.3-B.md:163`, `EXP-F4-A-MINITEST-RAMP-GOV-PLAN.md:107` | **NO VERIFICABLE** |
| T6 | `/tmp/opencode/run_variant.sh` | **PERDIDO** | ES-01 (workload sintético) | **NO VERIFICABLE** |
| T7 | `/tmp/opencode/rt_idle.csv` | **PERDIDO** | `FASE-D-ETAPA-3-PRECHECK.md:32,239` | **NO VERIFICABLE** |
| T8 | `/tmp/opencode/ep05_base.txt` | **PERDIDO** | `ep05…/scripts/{ab-e5,ab-e5-vk,env-check}.sh:3` | **HISTÓRICO** (no verificar; no sustit. por ruta inventada) |
| T9 | `/tmp/opencode/ep06_base.txt` | **PERDIDO** | `soak-final.sh:3`, `soak-probe.sh:3` (**SET H — F**) | **NO TOCAR** (Set H protegido); se registra en el plan, no se modifica el script |
| T10 | `/tmp/opencode/fase_b_base.txt` | **PERDIDO** | `fase-b…/driver.sh:3` | **HISTÓRICO** (ídem T8) |
| T11 | `/tmp/opencode/fakehome/.drirc` | **PERDIDO** | R-11 / workload | **NO VERIFICABLE** |
| T12 | `/tmp/opencode/f4a-smoke/`, `/tmp/opencode/f4a-s/` | **PERDIDO** | `PRE-FLIGHT-CALIBRACION-EXP-F4-A.md:15,27` | **NO VERIFICABLE** (preflight) |
| T13 | `/tmp/opencode/gpa311/` | **PARCIALMENTE RECUPERABLE** | R0-1 (fuente upstream GFX8) | sobrevive el extracto `R0-1-GFX8-EVENT-ID-REFERENCE.txt`; **documentar la recuperación parcial** (D7) |

**Ninguno se reconstruye. Solo se anota su estado. T9 no se toca (Set H).**

---

# 6. Los 8 documentos nuevos

| # | Nombre | Ubicación | Propósito | Fuentes que justifican su creación | Contenido mínimo |
|---|---|---|---|---|---|
| N1 | `FUENTES-FALTANTES.md` | `00-INDICE/` (decidir vs otra) | Inventario de UNKNOWN/fuentes pendientes | `REORGANIZATION-AUDIT.md:156,260,294`; UNKNOWNs ya en `open_questions.md` + `R1-7-CRITICAL-GAPS.md` | tabla: UNKNOWN → fuente buscada → estado → fecha |
| N2 | `IMPLEMENTATION-ROADMAP.md` | `01-AUDITORIA/IMPLEMENTATION-READINESS/` **o** `04-IMPLEMENTACION/` (a decidir) | Hoja de ruta de implementación | `IMPLEMENTATION-READINESS-AUDIT.md:927-928`; `REORGANIZATION-AUDIT.md:257` | fases ordenadas, dependencia, frontera de seguridad |
| N3 | `IMPLEMENTATION-SAFETY-RULES.md` | ídem | Reglas de seguridad (frontera de escrituras) | `IMPLEMENTATION-READINESS-AUDIT.md:927-928`; reglas hoy dispersas en `MASTER-RESEARCH-STATUS.md:348-357,393-400` | lista de NO AUTORIZADO + qué requiere autorización |
| N4 | Informe `rx550-power-sweep-20260918-132309` | `03-EXPERIMENTOS/rx550-power-sweep-20260918-132309/` | Declarar el sweep **no utilizable** | D3/power sweeps: 96× Intel HD 4600, `sclk_avg=0.0` | nota: “datos de iGPU, no RX550; histórico, no utilizable” |
| N5 | Informe `rx550-power-sweep-20260918-140527` | `03-EXPERIMENTOS/rx550-power-sweep-20260918-140527/` | Declarar **no utilizable cuantitativamente** | columnas desalineadas (`sclk_avg=0.0` vs `sclk_max=1071`) | nota: “columnas desalineadas; requiere parser; histórico” |
| N6 | Nota de estado `results/` | `03-EXPERIMENTOS/results/` | Registrar que no es un experimento | `results/logs/session1.log` = `BUILD FAILED` | nota: “build fallido, sin experimento” |
| N7 | Sección de índice para auditorías background | `00-INDICE/MASTER-RESEARCH-STATUS.md` (sección) | Indexar 4 auditorías + readiness | 4 `AUDITORIA-*`/`PROTOCOLO-*` untracked + `IMPLEMENTATION-READINESS-AUDIT.md` | tabla de las 5 con fecha y estado |
| N8 | Tabla de normalización de estados ES/EN | `00-INDICE/` (nuevo) | Vocabulario canónico | mezcla `INCONCLUSO`/`INCONCLUSIVE`, `PENDIENTE`/`PENDING`, `PARADA D`/`STOPPED` | tabla de equivalencias (propuesta del agente de trazabilidad) |

**Los 8 requieren autorización explícita de creación; N1–N3 tienen contenido justificable; N4–N6 son notas de estado; N7–N8 son de proceso.**

---

# 7. Los 6 documentos existentes que requieren actualización

| # | Documento | Cambios exactos propuestos | Decisión |
|---|---|---|---|
| U1 | `00-INDICE/MASTER-RESEARCH-STATUS.md` | ① Addenda fechada del estado R-4B v2.3 (§8) ② `:371` `rx550-torneo/` → `04-IMPLEMENTACION/rx550-torneo/` | D6 |
| U2 | `00-INDICE/MASTER-PLAN.md` | ① `:781` descripción de R-2.2 → estructura actual (mapa vivo) ② `:5` `PROJECT-ROADMAP.md` → nota de norte (o mantener) | D4 |
| U3 | `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` | 17 de 18 referencias (§10) | D2 |
| U4 | `README.md` (raíz) | `:21-29` narrativa de reorganización → estado actual | D1 |
| U5 | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | localizadores abreviados → completos | D1/D2 |
| U6 | `02-ARQUITECTURA/POLARIS12-MAP.md` | `:183,230` PCIe Gen3×8 y 2 ACE → separar capacidad/negociado/verificado; nota `:84,232` | — (contradicción M4) |

---

# 8. Cambios relacionados con R-4B (D6, D7)

### 8.1 Dónde aparece “no ejecutado” y qué debe decir

| Ubicación | Texto actual (extracto) | Cambio propuesto | Formato |
|---|---|---|---|
| `MASTER-RESEARCH-STATUS.md:3` | “PROPUESTA v2.3 PREPARADA (NO EJECUTADA) … S2 NO iniciada” | **Addenda fechada**: S1 v2.3 EJECUTADA/COMPLETADA; S2 v2.3 INICIADA/PARADA D; veredicto global **INCONCLUSO/INCONCLUSIVE** | ARCHIVO / CAMBIO / ANTES / DESPUÉS / EVIDENCIA / RIESGO / VERIFICACIÓN |
| `MASTER-RESEARCH-STATUS.md:278,310,332,387,406-424` | repetido | corregir o remitir a la addenda | ídem |
| `EXP-F4-A-PROTOCOL-v2.3.md:3-4` | “ninguna trial ejecutada” | marcar como **snapshot pre-ejecución** (no es contradicción a reparar: es histórico) | ídem |
| `EXP-F4-A-PROTOCOL-v2.3.md:224-230` | “S1/S2 autorizadas” | sin cambio (coherente) | — |
| `EXP-F4-A-RESULTADOS.md` (heredado) | conserva `TBD`, “S2 no inició”, cita `results/session2/` inexistente | marcar como **HISTÓRICO** (no vigente) | ARCHIVO / CAMBIO / ANTES / DESPUÉS / EVIDENCIA / RIESGO / VERIFICACIÓN |
| `AUDITORIA-PRE-RUN-v2.3.md:78-95` | dice que `results/v23` no existía | marcar como **snapshot pre-run** | ídem |

### 8.2 Formato de modificación (ejemplo principal: `MASTER-RESEARCH-STATUS.md`)

```
ARCHIVO: 00-INDICE/MASTER-RESEARCH-STATUS.md
CAMBIO:  Añadir addenda fechada con el estado canónico R-4B v2.3 (S1 ejecutada,
         S2 PARADA D, veredicto INCONCLUSO); NO reescribir el texto histórico.
ANTES:   línea 3 «…PROPUESTA v2.3 PREPARADA (NO EJECUTADA) … S2 NO iniciada…»
DESPUÉS: addenda al final de la sección R-4B: «R-4B v2.3 (addenda 2026-09-23):
         S1 EJECUTADA/COMPLETADA; S2 PARADA D (rc=9, inválida por interrupción);
         muestra incompleta; R7 INCONCLUSIVE; veredicto global INCONCLUSO.
         La descripción anterior (v2.2/no ejecutada) se conserva como historial.»
EVIDENCIA: EXP-F4-A-RESULTADOS-v2.3.md:3-5,11-32,152-166; results/v23/session1
         completo; results/v23/session2 parcial; results/logs/v23.done (PARADA, rc=9);
         ausencia de verdict.json (coherente con INCONCLUSO).
RIESGO: bajo si es addenda (no borra historia). El texto antiguo seguiría diciendo
         “no ejecutada”, mitigated con un puntero “ver addenda”.
VERIFICACIÓN POSTERIOR: grep de “INCONCLUSO/PARADA D” en el fichero; confirmar que
         el texto histórico permanece; git diff no toca results/.
```

### 8.3 Dónde registrar S1, S2 PARADA D e INCONCLUSO (ubicaciones D6 ya decididas)

- **Fuente canónica**: `EXP-F4-A-RESULTADOS-v2.3.md` (ya lo documenta; no cambiar veredicto).
- **Índice**: `MASTER-RESEARCH-STATUS.md` → addenda (§8.2).
- **Histórico**: `EXP-F4-A-RESULTADOS.md` → marcar como histórico, no vigente.
- **Readiness**: `IMPLEMENTATION-READINESS-AUDIT.md` ya refleja el estado v2.3 (verificado); sin cambio.

### 8.4 Cómo documentar los 13 artefactos `/tmp` perdidos (D7, sin reconstruirlos)

```
ARCHIVO: 03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md
CAMBIO:  Añadir nota al bloque que explica la PARADA D (líneas ~18, 165-166):
         los artefactos /tmp/opencode/micro12/vkmark30-telemetry.csv y
         /tmp/opencode/marcar_ventanas.py NO EXISTEN en el estado actual; la
         atribución a interferencia externa es CAUSA PROBABLE NO VERIFICABLE
         desde el repositorio. La telemetría principal (results/v23/) permanece
         como evidencia independiente.
ANTES:   referencia a /tmp/opencode/micro12/vkmark30-telemetry.csv sin estado
DESPUÉS: referencia + marca «PERDIDO / NO VERIFICABLE — no reconstruido»
EVIDENCIA: los 13 localizadores verificados como inexistentes; D7 adoptada.
RIESGO: bajo (aditiva, no altera el veredicto INCONCLUSO).
VERIFICACIÓN POSTERIOR: el veredicto sigue siendo INCONCLUSO; nota presente.
```

**Los 13** (incluidos los de Set H) se listan en **§5**; los de Set H (T9) **no se tocan** — su NO-GO se documenta aquí, no en los scripts.

---

# 9. Cambios relacionados con benchmarks (D3)

```
ARCHIVO: 05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md
CAMBIO:  ① Separar 3 conceptos (instalados / descargados-en-repo / ejecutados);
         ② asignar estado canónico por benchmark; ③ reparar 2 rutas (R6,R7);
         ④ eliminar/reformular “solo hay un benchmark” si aparece.
ANTES:   “4 instaladores instalados” vs “solo GravityMark descargado” (secciones
         separadas, sin eje común); Superposition a la vez “candidato” y
         “descartado”.
DESPUÉS: tabla de 3 ejes. Estado: GravityMark VALID (instalado + descargado +
         ejecutado, RESULTADO.md); Superposition INCONCLUSIVE (instalado,
         descarga .partial, ejecutado score 804 <27 W, RESULTADO-Superposition.md);
         Heaven HISTORICAL (instalado, sin resultado); Valley HISTORICAL (instalado,
         sin resultado). Formulación clave: “4 instalados, no 4 resultados válidos”.
EVIDENCIA: berchmark/instalados/ tiene los 4 (196M/337M/2.7G/520M, binarios);
         repo: 1 .run completo + 1 .partial; 03-EXPERIMENTOS tiene
         RESULTADO.md y RESULTADO-Superposition.md (0 resultados Heaven/Valley).
RIESGO: medio — cambiar BENCHMARK-INVENTORY afecta a la elegibilidad de M2.
VERIFICACIÓN POSTERIOR: los 4 estados presentes; las 2 rutas resuelven; la frase
         “4 instalados, no 4 resultados” presente; SIN afirmar causalidad.
```

```
ARCHIVO: 05-FUENTES-EXTERNAS/RX550_Benchmarks/README.md + docs/SOURCES-AND-EXECUTION.md
CAMBIO:  Reformular para que no contradigan al inventory: describen el estado de
         DESCARGAS, no el de instalaciones.
ANTES:   “contiene descargas sin instalar”, “solo GravityMark descargado”
DESPUÉS: “Descargas en el repo: 1 completa (GravityMark) + 1 parcial (Superposition).
         Instalaciones fuera del repo: 4 (ver BENCHMARK-INVENTORY). No confundir.”
EVIDENCIA: contenido real de official-downloads/ y cancelled-downloads/.
RIESGO: bajo.
VERIFICACIÓN POSTERIOR: coherencia con BENCHMARK-INVENTORY tras el cambio ①.
```

---

# 10. Cambios de README y R2-GLOBAL-DOCUMENTATION-MAP (D1, D2)

```
ARCHIVO: 00-INDICE/README.md
CAMBIO:  Convertir en ÍNDICE CANÓNICO de la estructura actual. 11 rutas:
         5 experiments/ → 03-EXPERIMENTOS/ (R1-R5); 6 ficheros movidos →
         02-ARQUITECTURA/ (RX550_BUILD_SPECIFICATION, knowledge, evidence,
         hypotheses, open_questions, research_log, rejected_ideas — note: 7
         ficheros, 6 rutas distintas más RX550_BUILD_SPECIFICATION). Añadir
         separación “índice canónico” vs “referencias históricas”. NO eliminar
         la nota histórica del backup (:31).
ANTES:   5 rutas experiments/ + 6-7 ficheros citados sin prefijo (rotos).
DESPUÉS: rutas con prefijo de 6 directorios; sección “Histórico” conserva el
         backup (:31) y la nota de que el documento refleja el árbol vigente.
EVIDENCIA: los 11 destinos existen (verificado); REGISTRO-DE-MOVIMIENTOS.md
         confirma el destino canónico; D1 adoptada.
RIESGO: medio — si se reescribe sin conservar la nota histórica, se pierde el
         registro de que el backup 17/09 es NO reproducible (línea 31).
VERIFICACIÓN POSTERIOR: los 11 destinos resuelven con test -e; la nota del backup
         sigue; el README no queda con rutas antiguas de árbol vigente.
```

```
ARCHIVO: 00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md
CAMBIO:  Mapa VIVO. Reparar 17 de 18 referencias (tabla D2.1 del informe de
         decisiones). Mantener la 1 histórica (backup, :172-173). Raíz antigua
         RX550_Iterative_Research/ puede permanecer como raíz histórica (D2).
ANTES:   18 refs a raíz antigua (líneas 23,31,40,44,130,134,138-144,166,172-175);
         raíz antigua vacía; projects/ y rx550-torneo/ ya no existen bajo ella.
DESPUÉS: raíz = RX550-INVESTIGACION/; capas = 6 directorios; 14 diseños FASE-R2
         → 04-IMPLEMENTACION/; mapa → 00-INDICE/; backup se mantiene como
         referencia histórica explícita.
EVIDENCIA: los 17 destinos actuales existen (verificado 1:1); REGISTRO-DE-
         MOVIMIENTOS.md:9 documenta el destino real; D2 adoptada.
RIESGO: ALTO — es el índice de navegación del proyecto; un error induce a editar
         rutas equivocadas en 10+ documentos. Mitigación: reparación referencia
         por referencia (no sustitución global), verificación test -e de las 17.
VERIFICACIÓN POSTERIOR: 17/17 resuelven; 1 histórica intacta; consumidores
         (MASTER-PLAN:781, PROJECT-DOC-STATUS:9) coherentes tras el cambio.
```

---

# 11. Elementos que permanecen INTOCABLES

| # | Elemento | Por qué | Verificación de no-tocar |
|---|---|---|---|
| P1 | **Set H — 10 scripts** | D8: protegidos; no scripts, hashes, contenido ni mtimes | los 10 SHA256 deben seguir coincidiendo byte a byte |
| P2 | `00-INDICE/REORGANIZACION-MANIFEST.sha256` | evidencia de integridad pre-movimiento (1.645 hashes) | sin cambios |
| P3 | 6 bitácoras: `REORGANIZATION-AUDIT`, `POST-REORGANIZATION-REFERENCES-AUDIT`, `POST-REORGANIZATION-REFERENCE-REPAIR-{PLAN,RESULT}`, `POST-REORGANIZATION-SET-I-{AUDIT,REPAIR-RESULT}`, `REGISTRO-DE-MOVIMIENTOS`, `REGISTRO-DE-REPARACION-REFERENCIAS` | registro histórico de la reparación A–G + Set I | sin cambios |
| P4 | CMake/Ninja generados (2 harnesses: `build/**`) | artefacto generado; se regenera, no se edita | sin cambios |
| P5 | JSON/logs de corrida (`m1-schedule.json`, `manifest.*`, `audit.json`, `stdout/stderr/log`, `state_*.txt`, `frozen.sha256`) | evidencia congelada de corridas | sin cambios |
| P6 | **388 ficheros de los 2 power sweeps** | evidencia histórica; añadir solo nota (N4/N5), no tocar datos | sin cambios en los 388 |
| P7 | **50 copias NotebookLM** (`RX550-INVESTIGACION-NOTEBOOKLM/`) | copia plana, 0 symlinks; NO convertir en symlinks, NO mover | 50 ficheros, 0 symlinks |
| P8 | Raíces históricas: `RX550_Iterative_Research/` (vacía), `RX550_Modo_Torneo_Backup_2026-09-19_0836/` | preserved; la raíz vacía **puede permanecer** (D2) | no borrar |
| P9 | `RX550_Iterative_Research/experiments/` vacío | resto histórico; no eliminar | 0 ficheros, no borrar |
| P10 | D5: los 3 (`FASE-E`, `FASE-F`, `SYNTHETIC-WORKLOAD-DESIGN`) | D5 cerrado: no tocar contenido ni hashes | sin cambios |
| P11 | D6: no borrar historia de R-4B (`EXP-F4-A-RESULTADOS.md`, `PROTOCOL-v2.3-PROPUESTA`, `AUDITORIA-PRE-RUN`) | solo **marcar** como históricos/snapshots | sin cambios |
| P12 | D7: los 13 artefactos `/tmp` | no reconstruir; solo anotar en documentos, nunca en Set H | no crear sustitutos |
| P13 | D10: sin commit | hasta el final | — |

---

# 12. Orden de ejecución propuesto (evitar referencias intermedias rotas)

**Principio**: (a) primero las hojas que nadie cita, (b) después los índices que las citan, (c) el README canónico y los documentos nuevos al final, (d) verificación tras cada paso. El árbol de trabajo quedará **temporalmente inconsistente hasta el commit final** (D10 lo acepta).

| Paso | Acción | Por qué en esta posición | Verificación |
|---|---|---|---|
| **1** | Hojas sin entradas: `FASE-G:7` (R8), `R4C/PRIOR-ART:99` (R9), `R2-HISTORICAL:54` (R10) | nadie depende de estas correcciones | `test -e` de los 3 destinos |
| **2** | Hojas `/tmp` (R12) + notas de no-verificable en R-4B/thermal/others (§5, §8.4) | aditivo; prepara el terreno de D6/D7 | notas presentes; veredictos intactos |
| **3** | `R2-HISTORICAL-EXPERIMENT-INVENTORY` y `BENCHMARK-INVENTORY` rutas rotas (R10 ya en 1; R6,R7 aquí) | benchmarks se reconcilian después | R6/R7 resuelven |
| **4** | **`R2-GLOBAL-DOCUMENTATION-MAP.md`** (17 refs, D2) | los índices maestros lo citan; se actualiza antes que ellos | 17/17 `test -e` |
| **5** | `MASTER-PLAN.md:781` (D4) | depende de que el mapa ya sea vivo (paso 4) | descripción refleja estructura actual |
| **6** | `MASTER-RESEARCH-STATUS.md` (addenda R-4B + `:371`) | el maestro debe reflejar el mapa (paso 4) y el veredicto (D6) | addenda presente; texto histórico intacto |
| **7** | `PROJECT-DOCUMENTATION-STATUS.md`, `POLARIS12-MAP.md` | coherencia con el mapa y R-4A | sin refs antiguas al mapa |
| **8** | `BENCHMARK-INVENTORY` + `README`/`SOURCES-AND-EXECUTION` (D3, 3 conceptos) | reconciliación semántica; puede ir tras el mapa | 4 estados canónicos presentes |
| **9** | `README.md` raíz (narrativa) + `00-INDICE/README.md` (D1, índice canónico) | el índice canónico va **último**: debe reflejar todos los pasos previos | 11 destinos resuelven; nota histórica conservada |
| **10** | Cabeceras `projects/` (11) + `run-m1.sh` (R11) | cosmético y script no ejecutado; al final | cabeceras con prefijo completo |
| **11** | Documentos nuevos N1–N8 | citan la estructura ya corregida | existen; no citan rutas antiguas |
| **12** | **Verificación global** + `git status` + **NO commit** (D10) | antes de decidir el commit | set de verificaciones §12-bis |

## §12-bis Verificación global tras la ejecución

1. `test -e` de los 17 destinos del mapa + los 11 del README canónico + R6–R10.
2. Los 10 SHA256 de Set H idénticos.
3. `git status` muestra solo los cambios esperados (contar: 14 archivos de §1 + cabeceras + R11 + 8 nuevos − los que Resulten “solo nota”).
4. `git diff --stat` no toca: Set H, manifiesto, 6 bitácoras, CMake/Ninja, JSON/logs, 388 power-sweep, 50 NotebookLM, raíces históricas, los 3 de D5.
5. Los 13 `/tmp` siguen sin crearse; no hay rutas inventadas.
6. Sin commit (D10).

---

**Fin del plan original (antes de la autorización).** No se había ejecutado ninguna reparación en la fase de planificación. Este era el único fichero creado/modificado en esa fase: `01-AUDITORIA/REPARATION-PLAN.md`.

**Estado original del plan (antes de la autorización):** se quedaba a la espera de autorización explícita para ejecutar las reparaciones.

---

## Addenda de ejecución — 2026-09-23

**Autorización:** recibida explícitamente para ejecutar las reparaciones, con las
restricciones D1–D10 y los límites adicionales fijados para R11, `/tmp`, N1–N3 y A22.

### R11 — trazabilidad

- Archivo: `03-EXPERIMENTOS/M1-cap-35-30/run-m1.sh`.
- Cambio único: `../../rx550-torneo` → `../../04-IMPLEMENTACION/rx550-torneo`.
- Destino verificado existente; diff limitado a esa línea; script no ejecutado.
- No se modificó ningún otro carácter del script.

### Ejecución por grupos

1. Hojas R8/R9/R10 y anotaciones D7/D9; T9 (`ep06_base.txt`) no se tocó por pertenecer a Set H.
2. R6/R7 y reconciliación D3 de benchmarks.
3. Mapa vivo R2-GLOBAL-DOCUMENTATION-MAP y descripción R-2.2 del MASTER-PLAN.
4. Addendas D6 de R-4B, marcación de snapshots pre-run y estado canónico INCONCLUSO.
5. Rutas de PROJECT-DOCUMENTATION-STATUS, corrección de alcance PCIe/ACE de POLARIS12-MAP y notas A22.
6. README raíz, índice canónico y las 11 cabeceras mecánicas de proyectos.
7. Documentos N1–N8; las notas de power sweeps y `results/` son ficheros nuevos, no
   alteración de los datos.
8. F7 (aliases R0 de `R1-5`) y F12 (extrapolación no lineal del mini-test) verificados
   y corregidos; no se generaron snapshots ni datos temporales.

### Desviaciones y límites conservados

- La auditoría de readiness solo recibió la actualización puntual de ubicación de N2/N3 y
  la marca D7 del localizador temporal ya citado; no se reescribieron sus conclusiones.
- Las referencias operativas a rutas históricas no se sustituyeron; se conservaron y, cuando
  era necesario, se marcó el estado PRE-REORGANIZACIÓN.
- El recuento global de localizadores temporales en documentos del proyecto incluye
  menciones adicionales de auditorías background; los 13 canónicos D7 quedan inventariados
  en `EXP-F4-A-RESULTADOS-v2.3.md`.
- No se ejecutó ningún script del proyecto, benchmark, servicio o código descargado.
- No se hizo commit.
- La comprobación final read-only de systemd mostró `system-autopilot.timer`, `kalm.service`,
  `kalm-lite.service` y `kalm-gpu.service` en `active/enabled`; no se reconcilió con los
  snapshots históricos que describen otro estado porque modificar servicios está fuera
  de este plan.

**Inventario de worktree:** 52 entradas están directamente atribuibles a este plan
(incluidas las nuevas N1–N8 y notas); las 40 entradas restantes que aparecen en
`git status` son cambios previos de reorganización/auditoría conservados, no se
reinterpretan ni se mezclan en esta reparación. La lista exacta se entrega en el informe
final de esta ejecución.
