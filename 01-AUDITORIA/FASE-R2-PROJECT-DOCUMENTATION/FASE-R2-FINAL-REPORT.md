# FASE-R2-FINAL-REPORT — Informe Final de FASE R-2 (COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE)

> **Archivo:** `FASE-R2-FINAL-REPORT.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.25)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL Y DE DISEÑO
> **Clasificación:** [COMPLETADA] Fase cerrada; ningún ítem "ejecutado" marcado por el hecho de estar diseñado.
> **Lugar:** `experiments/FASE-R2-PROJECT-DOCUMENTATION/`

---

## A. OBJETIVO Y ALCANCE DE LA FASE

Documentar **todo el trabajo pendiente del ecosistema completo** (no solo RX 550/GFX8) para que cualquier
investigador futuro pueda: (1) entender QUÉ existe y QUÉ falta, (2) ejecutar cada fase leyendo su diseño sin
inventar el protocolo, (3) distinguir rigurosamente DOCUMENTADO/DISEÑADO/PLANIFICADO/INVESTIGADO/OBSERVADO/
MEDIDO/REPRODUCIDO/VALIDADO/HIPÓTESIS/UNVERIFIED/BLOCKED/DEFERRED/NOT STARTED/NO AUTORIZADO, y (4) no promover
ningún nombre provisional a tecnología consolidada sin evidencia.

**Alcance:** inventario histórico E0–E5, mapa documental global, diseños formales de las fases E–Q, matriz de
prioridad (J), diseño del workload sintético modular, nomenclatura del ecosistema (N), 4 proyectos propios,
grafo de dependencias, índice central en raíz, y actualización de MASTER-PLAN/MASTER-RESEARCH-STATUS.

## B. MODO DE TRABAJO Y CONSTANTES

1. **Solo documental/diseño:** ninguna escritura de sistema; sin tocar hardware, kernel, Mesa, PowerPlay,
   VBIOS o BIOS; sin contadores, sin benchmarks nuevos. Sin implementar BERRETA/Ghost/RX-Comp/Orquestador.
2. **Rigor de estados:** nunca "completo" porque exista un párrafo en MASTER-PLAN; diseño suficiente = otro
   investigador puede ejecutarlo sin inventar el protocolo.
3. **Nada se inventa:** E0 registrado como NOT FOUND con dónde se buscó; proyectos provisionales marcados
   PROVISIONAL/IDEA.
4. **Programación de contadores y toda escritura de sistema SIGUEN NO AUTORIZADAS** (invariante heredado).

## C. ESTADO DEL ECOSISTEMA ANTES DE R-2

- Fases cerradas con evidencia: **A** (discriminación), **B** (cap-probe + POLARIS12-MAP), **C**/*R-14*
  (Superposition), **EP-05/EP-06** (CUSTOM=STOCK; soak no reproduce E1/E3), **FASE D etapas 1–2** (auditoría
  read-only, contraste A/B 1.41), **M1** (vkmark 35/30W, 112/112), **WORKLOAD-SINTETICO** (E-01..E-03/ES-01/F2
  VERIFICADO), **R-0** (catálogo GFX8 vía GPUPerfAPI v3.11.1, GRBM=2 y SQ=4 VALIDADOS), **R-1** (reconciliación
  GFX8, mapa A–R-1, capa transversal, readiness E–J).
- **FASE D etapa 3**: DISEÑADA + PRECHECK + EVENTOS + AUDITORÍA completadas; ejecución NO autorizada.
- Herramienta operativa **rx550-torneo** validada (65/55/56/112 checks). Benchmarks instalados verificados.
- **No existía ningún diseño de E→Q** con especificación ejecutable; **no existía `projects/`** (creado).

## D. INVENTARIO HISTÓRICO (E0–E5) Y FAMILIA 2

Verificado contra el backup Torneo (`RX550_Modo_Torneo_Backup_2026-09-19_0836/experiments/`):

| Experimento | Encontrado | Ubicación | Nota |
|---|---|---|---|
| **E0** | **NOT FOUND** como artefacto | `mesa-resolution-…113618` y `mesa-resolution-…135118` (datos plausibles SIN etiquetar) | solo 2 refs textuales: E1 manifest l.9 "power1_cap=25W como en E0"; E1-report l.53 "1080→480 ×7.4" |
| **E1** | SÍ | `mesa-e1-20260917-170430/` (E1-report.md) | — |
| **E2** | SÍ | `mesa-e2-…175132/` (raw) + `mesa-e2-…175301/` (E2-report.md, e2_summary.tsv) | — |
| **E3** | SÍ | `mesa-e3-20260917-213646/` (GPU-BOTTLENECK-report.md) | **E4/E5/E5b son subdirectorios** (e4/, e5/, e5b/ + m1/raw = histórico M1, NO el M1 autorizado) |
| **E4** | SÍ (subdir e3) | `mesa-e3-…/e4/E4-report.md` | power-limit vs unit-limit; DPM high @25W degrada |
| **E5** | SÍ (subdir e3) | `mesa-e3-…/e5/E5-report.md` | cap removido → 35W, ×2–4 perf, 88–92 °C |
| **E5b** | SÍ (subdir e3) | `mesa-e3-…/e5b/E5b-report.md` | SCLK fijo 214 MHz → misma penalización a 25/35W; ALU descartada; SCLK:MCLK enmascara costes de memoria |
| **Familia 2** | SÍ VERIFICADA | `WORKLOAD-SINTETICO/` | E-01/E-02/E-03 (13.4/15.75 W) + ES-01 + F2; reproducible |

**Conclusión:** dos familias "E" distintas (histórica Torneo 17/09 vs WORKLOAD-SINTETICO), documentadas por
separado y **no mezclables**. Cualquier referencia a "E3" debe aclarar la familia.

## E. MAPA DOCUMENTAL GLOBAL Y NAVEGACIÓN

- `R2-GLOBAL-DOCUMENTATION-MAP.md` (R-2.2): árbol completo del repositorio (raíz, `experiments/` A–D/R-0/R-1/
  sintético/R-2, `rx550-torneo/`, backup, `projects/`) con rutas de navegación para investigador nuevo.
- `PROJECT-DOCUMENTATION-STATUS.md` (R-2.24, en raíz): índice central **por elemento** (fases, proyectos,
  infraestructura) con las 7 preguntas (existe/falta/diseñado/ejecutado/validado/planteado/autorizado).

## F. DISEÑOS DE FASES E–Q (todos DISEÑADOS, ninguno ejecutado)

| Fase | Archivo | Contenido esencial | Estado |
|---|---|---|---|
| **E** | `FASE-E-REAL-GAME-BASELINE-DESIGN.md` | baseline de juego real (selección, NS≥30s, telemetría unificada, VALID/INVALID/OUTLIER/REPEATABLE) | DISEÑADA — **BLOQUEADA** (sin juego reproducible autorizado) |
| **F** | `FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md` | GEO-01..08 (hipótesis/mecanismo/contador potencial/workload/riesgos/confounders/éxito-negativo) | DISEÑADA |
| **G** | `FASE-G-MEMORY-VRAM-GTT-DESIGN.md` | modelo request→caches→VRAM/GTT→PCIe→RAM→stall; G-M1..G-M5 | DISEÑADA |
| **H** | `FASE-H-RADV-WORKAROUNDS-DESIGN.md` | H-1..H-7 (MSAA sample loc, LINE_FILTER, clear_db_cache, z_fights/blend, shrink_image_store, wait_for_vm_map, partial_vs_wave) | DISEÑADA |
| **I** | `FASE-I-POWERPLAY-DPM-DESIGN.md` | separación A–F; política MCLK 5/16/20; I-1..I-5 | DISEÑADA |
| **J** | `EXPERIMENT-PRIORITY-MATRIX.md` | 10 criterios → ALTA/MEDIA/BAJA/BLOQUEADOS | DISEÑADA |
| **K** | `FASE-K-PERFORMANCE-LAB-DESIGN.md` | K1..K10 (telemetría, runner, dataset, repeticiones, warmup, validación, fault detection, perturbación de observabilidad, capability matrix, hashing) | DISEÑADA |
| **L** | `FASE-L-RX550-TUNER-DESIGN.md` | state machine + ownership + lock + verificación + failsafe; no reemplaza rx550-torneo | DISEÑADA |
| **M** | `FASE-M-GFX8-COUNTER-RESEARCH-DESIGN.md` | estado del catálogo (R-0.1/R1-1) → rutas M-A..M-E; "Event ID documentado ≠ autorización" | DISEÑADA |
| **N** | `FASE-N-ECOSYSTEM-ARCHITECTURE.md` | 14 nombres oficiales, SAFETY BOUNDARY, ciclo de vida | DISEÑADA |
| **O** | `FASE-O-GPU-CONTROL-ORCHESTRATION-DESIGN.md` | LACT/CoreCtrl/amdgpu-clocks vs rx550-torneo (capacidades/ownership/…); externas = objetos de evaluación, sin instalación | DISEÑADA |
| **P** | `FASE-P-FRAME-GENERATION-UPSCALING-DESIGN.md` | lsfg-vk/FSR/upscaling; separación REAL FPS vs GENERATED vs PERCEIVED; nunca en Lab K | DISEÑADA |
| **Q** | `FASE-Q-MESA-POLARIS12-OPTIMIZATION-DESIGN.md` | inventario por dominio (radeonsi/RADV/ACO/LLVM/memoria), ficha 10 campos, pipeline OBSERVACIÓN→…→DECISIÓN; sin tocar Mesa | DISEÑADA |
| **SINTÉTICO** | `SYNTHETIC-WORKLOAD-DESIGN.md` | framework modular 8 modos sobre prototipo CONGELADO | DISEÑADA |

## G. PROYECTOS PROPIOS (creado `projects/`; 4 diseños, ninguno implementado)

| Proyecto | Archivo | Naturaleza | Dependencias |
|---|---|---|---|
| **BERRETA** | `projects/BERRETA/BERRETA-DESIGN.md` | investigación de overlap async/ACE (H-B1..B3) | ASY-01, modelo de memoria G, Lab K |
| **Ghost / Ghost Cache** | `projects/GHOST/GHOST-CACHE-DESIGN.md` | prefetch/localidad/working set | G-M1/G-M5; separado GHOST vs GHOST-CACHE vs Tuner vs FASE G |
| **RX Compression Engine** | `projects/RX-COMPRESSION-ENGINE/RX-COMPRESSION-ENGINE-DESIGN.md` | compresión de memoria (texturas/buffers/intermedios/GTT/PCIe) | G-M2/G-M4, síntesis |
| **Orquestador Final** | `projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` | integración runner/telemetría/benchmark/tuner/contadores/validación/rollback/artefactos/decisión | K, L, M, O, P, Q — sin autoridad de HW |

## H. MATRIZ DE PRIORIDAD (FASE J)

`EXPERIMENT-PRIORITY-MATRIX.md` establece 10 criterios de priorización (valor de medición, dependencias,
riesgo, reversibilidad, reproducibilidad, coste, métricas, evidencia previa, poder de discriminación,
confounders) con puntuación justificada → ALTA/MEDIA/BAJA/BLOQUEADOS. **No hay "mejor experimento" sin
justificación explícita**; cada entrada traza su fundamento.

## I. WORKLOAD SINTÉTICO (diseño modular)

`SYNTHETIC-WORKLOAD-DESIGN.md`: framework de **8 modos** (geometry, shading, memory, fetch, vram, compute,
async, power) sobre el **prototipo CONGELADO** (no reescrito); superficies dinámicas, GPUs, CPU, control de
carga, sincronización CPU-cola, hashing/determinismo, validación de salida. Es la red de seguridad sobre la
que se construirán las futuras cargas del Lab K.

## J. DEPENDENCIAS Y GRAFO DEL ECOSISTEMA

`R2-DEPENDENCY-GRAPH.md` (R-2.21) trazable:
- **CONFIRMADA:** R-0→R-1→M; M→FASE D-3 (persistencia del catálogo); WORKLOAD→R-2.9/F/G;
  F/G/H/I→J; J→K; K→L/M; L→M/I; K/L/M/O/P/Q→Orquestador.
- **PROBABLE:** WORKLOAD→H (H-1 interpreta E3/E5); P→E; O→Orquestador; L→G-M3; P/E→G.
- **POTENCIAL (dependen de evidencia que aún no existe):** G→GHOST (G-M1/M5); G→RX-Compression (G-M2/M4);
  H→Q; F/H/I→BERRETA (debe validar ASY-01).
- **Lectura clave:** el cuello de implementación es **K→L/M** y la ejecución de F/G; Ghost y RX-Compresion
  están **genuinamente bloqueados por falta de señal experimental** en G.

## K. ESTADO DE AUTORIZACIONES Y GUARDAS (sin cambios respecto a R-1/R-0)

- ❌ **NO AUTORIZADO/NO EJECUTADO en R-2:** ninguna escritura de sistema (sysfs/MMIO/PowerPlay/pp_*/VBIOS/
  BIOS), programación de contadores (FASE D-3/M), benchmarks nuevos, instalaciones (juegos, LACT, CoreCtrl,
  amdgpu-clocks, lsfg-vk, plugins), modificación de Mesa (ni system ni /opt), de kernel, de WORKLOAD-SINTETICO.
- ✅ **Autorizado (read-only):** inventario/lectura de archivos, análisis de resultados históricos, diseño,
  lectura de código fuente local de Mesa (FASE M-A), cálculo documental.
- **WRITE SUCCESS ≠ STATE CHANGE VERIFIED** (invariante R1-8) se conserva como regla para cualquier futuro
  tuner L.

## L. GAPS, BLOQUEOS Y RIESGOS PENDIENTES

1. **FASE E bloqueada** (falta un juego real reproducible y autorizado como baseline).
2. **Lab K y launcher sintético (8 modos) sin implementar** — requeridos para F/G/H/I/L/M.
3. **Ghost y RX-Compression-Engine pendientes de señal en FASE G** (riesgo de quedar solo conceptuales).
4. **Semántica del bloque MC (contadores) UNRESOLVED** (heredado de R-1): no diseñar normalización de ancho
   de banda MC sobre ella.
5. **Riesgo de hibridación** entre Familias "E" si no se cita la familia explícitamente (mitigado en D).
6. **Herramientas externas (O/P)** podrían tener más margen que code-GEM UFIX: la evaluación de LACT/CoreCtrl
   y FG/upscaling queda documentada como objeto de evaluación futura, sin adopción.

## M. VERIFICACIÓN DE INTEGRIDAD — CHECKLIST DE FINALIZACIÓN (27 elementos)

### Entregables (R-2.1 … R-2.25)

| # | Ítem | Archivo | Estado |
|---|---|---|---|
| 1 | R-2.1 Inventario histórico E0–E5 | `R2-HISTORICAL-EXPERIMENT-INVENTORY.md` | ✅ COMPLETADA |
| 2 | R-2.2 Mapa documental global | `R2-GLOBAL-DOCUMENTATION-MAP.md` | ✅ COMPLETADA |
| 3 | R-2.3 Diseño FASE E (real-game) | `FASE-E-REAL-GAME-BASELINE-DESIGN.md` | ✅ DISEÑADA/BLOQUEADA |
| 4 | R-2.4 Diseño FASE F (geometry GEO-01..08) | `FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md` | ✅ DISEÑADA |
| 5 | R-2.5 Diseño FASE G (memoria G-M1..M5) | `FASE-G-MEMORY-VRAM-GTT-DESIGN.md` | ✅ DISEÑADA |
| 6 | R-2.6 Diseño FASE H (workarounds H-1..7) | `FASE-H-RADV-WORKAROUNDS-DESIGN.md` | ✅ DISEÑADA |
| 7 | R-2.7 Diseño FASE I (PowerPlay/DPM I-1..5) | `FASE-I-POWERPLAY-DPM-DESIGN.md` | ✅ DISEÑADA |
| 8 | R-2.8 Matriz de prioridad J | `EXPERIMENT-PRIORITY-MATRIX.md` | ✅ DISEÑADA |
| 9 | R-2.9 Diseño workload sintético (8 modos) | `SYNTHETIC-WORKLOAD-DESIGN.md` | ✅ DISEÑADA |
| 10 | R-2.10 Diseño FASE K (Lab K1..10) | `FASE-K-PERFORMANCE-LAB-DESIGN.md` | ✅ DISEÑADA |
| 11 | R-2.11 Diseño FASE L (Tuner) | `FASE-L-RX550-TUNER-DESIGN.md` | ✅ DISEÑADA |
| 12 | R-2.12 Diseño FASE M (contadores GFX8) | `FASE-M-GFX8-COUNTER-RESEARCH-DESIGN.md` | ✅ DISEÑADA |
| 13 | R-2.13 Diseño FASE N (ecosistema ARQ) | `FASE-N-ECOSYSTEM-ARCHITECTURE.md` | ✅ DISEÑADA |
| 14 | R-2.14 Diseño BERRETA | `projects/BERRETA/BERRETA-DESIGN.md` | ✅ DISEÑADA/IDEA |
| 15 | R-2.15 Diseño Ghost/Ghost-Cache | `projects/GHOST/GHOST-CACHE-DESIGN.md` | ✅ IDEA |
| 16 | R-2.16 Diseño RX-Compression-Engine | `projects/RX-COMPRESSION-ENGINE/RX-COMPRESSION-ENGINE-DESIGN.md` | ✅ IDEA |
| 17 | R-2.17 Diseño Orquestador | `projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` | ✅ DISEÑADA |
| 18 | R-2.18 Diseño FASE O (gestores/control GPU) | `FASE-O-GPU-CONTROL-ORCHESTRATION-DESIGN.md` | ✅ DISEÑADA |
| 19 | R-2.19 Diseño FASE P (frame gen/upscaling) | `FASE-P-FRAME-GENERATION-UPSCALING-DESIGN.md` | ✅ DISEÑADA |
| 20 | R-2.20 Diseño FASE Q (Mesa Polaris12) | `FASE-Q-MESA-POLARIS12-OPTIMIZATION-DESIGN.md` | ✅ DISEÑADA |
| 21 | R-2.21 Grafo de dependencias | `R2-DEPENDENCY-GRAPH.md` | ✅ COMPLETADA |
| 22 | R-2.22 MASTER-PLAN actualizado (§S) | `MASTER-PLAN.md` | ✅ COMPLETADA |
| 23 | R-2.23 MASTER-RESEARCH-STATUS actualizado (v2.6) | `MASTER-RESEARCH-STATUS.md` | ✅ COMPLETADA |
| 24 | R-2.24 Índice central en raíz | `PROJECT-DOCUMENTATION-STATUS.md` | ✅ COMPLETADA |
| 25 | R-2.25 Este informe final | `FASE-R2-FINAL-REPORT.md` | ✅ COMPLETADA |

### Garantías de la fase (globales)

| # | Ítem | Verificación | Estado |
|---|---|---|---|
| 26 | **Sin escritura de sistema durante R-2** | ningún sysfs/pp*/contador/instalación/benchmark modificado | ✅ VERIFICADO |
| 27 | **Coherencia entre fuentes + no promoción** | MASTER-PLAN §S ↔ MASTER-RESEARCH-STATUS v2.6 ↔ índice raíz coherentes; todo "DISEÑADO/IDEA/PROVISIONAL" sin marcar como ejecutado/validado | ✅ VERIFICADO |

## N. RESUMEN Y CONCLUSIONES (11 puntos)

1. **Fase cerrada** como SOLO DOCUMENTAL Y DE DISEÑO: no se ejecutó ningún experimento ni se tocó el sistema.
2. **Documentos creados:** 24 en `experiments/FASE-R2-PROJECT-DOCUMENTATION/` + índice raíz
   `PROJECT-DOCUMENTATION-STATUS.md`; **modificados:** `MASTER-PLAN.md` (§S) y `MASTER-RESEARCH-STATUS.md` (v2.6).
3. **Proyectos propios encontrados/creados:** `projects/` NO existía; se creó con BERRETA, Ghost, RX-Compression-Engine
   y Orquestador (4 diseños; ninguno implementado; 3 marcados PROVISIONAL/IDEA).
4. **Inventario histórico:** E1/E2/E3/E4/E5/E5b EXISTEN en el backup Torneo; **E0 = NOT FOUND** como artefacto
   (datos plausibles sin etiquetar); familia 2 (E-01..03/ES-01/F2) VERIFICADA. Dos familias "E" documentadas por separado.
5. **Fases diseñadas sin ejecutar:** E (bloqueada), F, G, H, I, J, K, L, M, N, O, P, Q — todas con especificación
   ejecutable por un investigador nuevo.
6. **Hipótesis recogidas y NO promovidas:** MSAA/raster (H), SCLK:MCLK (E5b), cache/memoria (G), overlap async
   (BERRETA), compresión (#RX-Comp), prefetch/localidad (Ghost), FG/upscaling (P) — todas como HIPÓTESIS/POTENCIAL.
7. **Dependencias trazadas:** grafo CONFIRMADA/PROBABLE/POTENCIAL; cuello de ejecución en K→L/M y ejecución F/G;
   Ghost/RX-Comp bloqueados por señal de G.
8. **Gaps pendientes:** FASE E sin juego autorizado; Lab K y launcher sintético sin implementar; semántica MC
   UNRESOLVED (heredada); instalación de externas (O/P) sin autorización.
9. **Autorizaciones sin cambio:** programación de contadores y toda escritura siguen NO AUTORIZADAS; read-only
   sigue permitido; WRITE SUCCESS ≠ STATE CHANGE VERIFIED vigente.
10. **Sin modificación del ecosistema verificado:** hardware 1002:699f, Mesa system/custom, kernel, algoritmo
   WORKLOAD-SINTETICO y rx550-torneo intactos (checks M/#26).
11. **Roadmap resultante:** implementar con autorización el **Lab K** y el **launcher sintético**; ejecutar
    read-only G-M1/M5 y F/G priorizados por J; luego L/M (writes en marco L); evaluar O/P de forma aislada; ascender
    proyectos PROVISIONAL solo con evidencia del pipeline Q/G.

## O. SIGUIENTES PASOS (fuera de R-2)

1. Autorizar y diseñar la implementación del **Lab K (K1..K10)** y del **launcher del workload sintético (8 modos)**.
2. Ejecutar fundamento read-only del modelo de memoria (**G-M1/M5**) y exploración de geometría (**F**) según J.
3. Revisar FASE Q (M-A) tras M: lecturas de Mesa locales; proponer cambios aislados bajo pipeline de validación.
4. Proponer a gobernanza la evaluación de FASE O/P y la instalación de un juego para FASE E.
5. Mantener actualizado el índice `PROJECT-DOCUMENTATION-STATUS.md` con cada nueva entrada del ecosistema.