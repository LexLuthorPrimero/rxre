# IDEATION-ROUND-02 — Fase de ideación divergente

**FECHA:** 2026-09-27 · **TIPO:** ideación sistemática · **ORIGIN=GENERATED_SYSTEMATICALLY**
· **NO_IMPLEMENTADO · NO_EJECUTADO · NO_ES_HIPÓTESIS**

> Documento **nuevo y separado**. `IDEA-REGISTER.md` **no fue modificado**.
> Este documento **no crea hipótesis, ni experimentos, ni evidencia**. Su
> único producto es un conjunto de *preguntas* con la procedencia del mecanismo
> que las generó y el discriminante que las separaría.

| | |
|---|---|
| `BASE` | 184 ideas de `IDEA-REGISTER.md` (`34e4268afb00ef48`) + corpus del proyecto |
| `FUENTE_DE_LAS_IDEAS_NUEVAS` | literatura técnica externa como **GENERADOR**, nunca como evidencia local |
| `REGLA` | una idea es `GENUINELY_NEW` sólo si difiere sustantivamente en ≥1 de: mecanismo, VI, VD, relación, escala, dominio temporal, dominio espacial, representación, recurso, contradicción, interacción, frontera, método, fenómeno ausente. Si sólo cambia nombre/parámetro/magnitud ⇒ `VARIANT_OF`/`DUPLICATE_OF` |
| `OBJETIVO` | cobertura del espacio de investigación, **no** volumen de ideas |

---

## 1. MÉTODO UTILIZADO

| # | Fase | Herramienta | Resultado |
|--:|---|---|---|
| `F0` | Verificación de fuente | `grep` de 36 términos candidatos en las 184 ideas | **36/36 AUSENTES** ⇒ mapa de huecos objetivo |
| `F1` | Mapa de espacios vacíos | 17 categorías `A`–`Q` | §3 |
| `F2` | Generación | 14 mecanismos (contradicción, inversión, fronteras, descomposición, recombinación, representación, analogía, recursos, negativos, medición, escala, tiempo, migración de cuello, representación差) | §6 |
| `F3` | Matriz morfológica | 14 dimensiones × alternativas del corpus | §4 |
| `F4` | TRIZ | 40 principios inventivos + matriz de contradicciones (Altshuller) | §5 |
| `F5` | Analogía | 6 dominios externos → mecanismo abstracto | §5.2 |
| `F6` | Ataque adversarial | 15 criterios por candidata | §6.3 (tasa de rechazo: **61 candidatas → 16 sobreviven**) |
| `F7` | Clasificación | 7 estados | §6 |
| `F8` | Literatura | Wikipedia GCN (HTTP 200), Wikipedia TRIZ (HTTP 200), Wikipedia Morphological analysis (HTTP 200, *stub* sin contenido útil) | §5.3 |
| `F9` | Control de novedad | 2 pasadas inversas | §12 |

## 2. CORPUS ANALIZADO

| Fuente | Estado | Rol |
|---|---|---|
| `IDEA-REGISTER.md` `34e4268a` | 184 ideas, 535 L | base de deduplicación |
| `AGENTS.md` `d346a441` | autoridad | restricciones (`NO_HOST_WRITE`, `OWNERSHIP`, evidencia) |
| `00-INDICE/HYPOTHESIS-REGISTER.md` `8bfa7e4c` | H1–H12 | preguntas existentes |
| `…/POLARIS12-MAP/EXPERIMENT-CANDIDATES.md` `d34a48c7` | 23 candidatos G/M/F/S/A/P | base de variantes |
| `02-ARQUITECTURA/open_questions.md` `5e53c4ab` | O-PHY/O-MCLK/O-BOT/O-Mesa/O-FPS/O-ROOT/O-P0-ENV | huecos declarados |
| `02-ARQUITECTURA/rejected_ideas.md` `82ff4857` | R-01..R-09 | negativos invertibles |
| `…/COUNTERS-ASIC-…ADDENDUM` `30bfecb5` | 5 capas de soporte, 5 `NOT_AVAILABLE` | límites de medición |
| `FASE-D-ETAPA-3-PLAN.md` | Q1–Q7 | preguntas bloqueadas por selectores |
| `R1-20260926T030435Z.json` `8806311b` | 12 clientes GPU, 2 GPUs presentes | contexto de host |
| `05-FUENTES-EXTERNAS/…/R0-2, R0-3` | PowerPlay MCLK, workarounds Mesa | contexto externo ya en corpus |

---

## 3. MAPA DE HUECOS (FASE 1)

### A. `VARIABLES_YA_EXPLORADAS` (no huecos)
SCLK · MCLK · power cap · temperatura · resolución · MSAA · layers/overdraw · draw calls · batch/submit · VBO/IBO · working set · VRAM/GTT · frame queue depth · presentation mode · blend · attachment format · ILP/occupancy · barrier count · profile × workload · counters (indirectos)

### B. `VARIABLES_PARCIALMENTE_EXPLORADAS`
ocupancy (como eje, no como *recurso limitante*) · cache (sólo vía bandwidth) · latencia (submit→fence; no doorbell→start) · energía (como `work/joule`; no como *energía por fase*) · firmware (**explícitamente fuera de alcance**, `FASE-D-ETAPA-3-PLAN:66`)

### C. `VARIABLES_NO_EXPLORADAS` — 36/36 confirmadas ausentes

`texture filter` · `aniso` · `trilinear` · `mip` · `LOD bias` · `bank conflict` · `TLB` · `page size` · `hugepage` · `NUMA` · `doorbell` · `scanout` · `underrun` · `preempt` · `time-slice` · `arbitration` · `contention` · `LDS` · `shared memory` · `SMC` · `uniform datapath` · `replay` · `retirement` · `power domain` · `duty cycle` · `effective frequency` · `firmware` · `fuses` · `PSP` · `noise floor` · `repeatability` · `run-to-run` · `negative control` · `second GPU` · `other GPU` · `i915` · `Kalm`

### D–E. `RELACIONES`
`ESTUDIADAS`: cap↔SCLK, cap↔W_SMU, workload↔clocks, MCLK↔working-set, VS↔occupancy, layers↔raster, MSAA↔DCC, perfil↔workload, IP↔W_SMU, temp↔SCLK (histórico)
`NO_ESTUDIADAS`: **GPU-A↔GPU-B**, **proceso-A↔proceso-B**, **doorbell↔inicio-de-trabajo**, **TLB↔page size**, **textura↔filtro**, **LDS↔bank**, **sensor↔estimador**, **ruido-de-medición↔tamaño-de-efecto**

### F–G. `MECANISMOS`
`PRESENTES`: cuellos de botella · histéresis · migración · ceilings · perturbación · descomposición · analogía · recombinación
`AUSENTES`: **arbitraje de contexto** · **preemption** · **gateway de dominio de energía** · **validez del sensor** · **mining de artefactos** · **control negativo** · **piso de ruido**

### H–I. `ESCALAS`
`PRESENTES`: shader · draw · frame · workload · process (parcial) · driver
`AUSENTES`: **entre-runs (repeatability)** · **entre-procesos** · **por-ciclo-térmico** · **por-historial** · **instrucción** · **transitorio-a-us** (doorbell→start)

### J. `RECURSOS_NO_UTILIZADOS`
Texture Filter Units (4/SIMD) · Texture Fetch/Load-Store Units (16/SIMD) · LDS 64 KiB + 8 KiB SGPR file · TLB · doorbell/queue HW · power domain · sensor estimator · **el segundo GPU del host** · los **artefactos preservados** (1321 mediciones nunca revalidadas, `DOCUMENTATION-CENSUS.md:284`)

### K. `CONTRADICCIONES` — 5 registradas, 2 sin idea resoluble (§11)

### L. `ANOMALÍAS`
`R1-20260926T030435Z.json`: dos GPUs activas a la vez (`renderD128`/`card0` en otro, `renderD129`/`card1` en RX550) y `kwin_wayland` con 9 FDs en `renderD128` **y** 9 en `renderD129`. El corpus nunca trata la segunda GPU como variable.

### M. `NEGATIVOS_INVERTIBLES` (7)
`R-01` cap no liga · `R-04` SCLK bajo no baja FPS GL · `R-08` Mesa CUSTOM ≈ STOCK · `R-06` E1 usó otro runner · `C1` `NOT_EXECUTED` · `H1` M1 no discriminó · `O-ROOT` sin causa

### N. `LIMITACIONES_DE_MEDICIÓN` (5)
PMU GFX8 `NOT_AVAILABLE` · `VK_KHR_performance_query` RADV GFX8 `NOT_AVAILABLE` · `frequency_effective_estimate=NOT_AVAILABLE` · `mem_busy_percent` es proxy · `W_SMU` es estimador

### O. `HIPÓTESIS_CUYA_REFUTACIÓN_GENERA_OTRA`
`H1` (si el cap no liga, la variable de demanda es otra) · `H7` (si la histéresis es de política y no de runtime, el objeto es el runtime) · `H12` (si no es WSI, es queue)

### P. `IDEAS_BLOQUEADAS` (7)
`P-02` MCLK forcing `CONGELADO` · `P-03` heating `CONGELADO` · `Q1..Q7` selectores prohibidos · `H4/H5` ASPM capability audit pendiente · `OWNERSHIP=FULL` inalcanzable con cliente activo

### Q. `FENOMENOS_SOLO_INDIRECTOS` (5)
`W_SMU` (estimador, nunca vatímetro) · `gpu_busy` (agregado, nunca "trabajo") · `MCLK` (reloj, nunca bandwidth) · `active_gpu_clients=12` (conteo, unidad sin verificar) · `DEBUGFS clients` (4 `drm_file` / 2 `tgid`, relación con los 12 sin establecer)

---

## 4. MATRIZ MORFOLÓGICA (FASE 3)

| Dimensión | Alternativas presentes en el corpus | Hueco combinado |
|---|---|---|
| `WORKLOAD` | sintético (`E-03`), `vkmark`, jellyfish 640p, UNIGINE, GravityMark | **multi-proceso** · **carga segundo GPU** |
| `GEOMETRY` | VS/FS/layers/instancing/primitivas/triángulos/overdraw | — (saturado) |
| `SHADER` | ILP/occupancy/precision/cross-lane/registros | **filtro de textura** · **SMC/uniform path** · **LDS bank** |
| `MEMORY` | working-set/GTT/VRAM/localidad/MLP/compresión | **TLB/page size** |
| `SUBMISSION` | draws/batch/CMD/descriptor/pipeline-state | **doorbell→start** |
| `QUEUE` | nº colas, async overlap, profundidad | **arbitraje entre contextos** |
| `SYNC` | barreras (scope/stage/access/batching/placement) | saturado |
| `WSI` | present rate/mode/queue depth/buffering | **scanout/underrun** |
| `CLOCK` | SCLK/MCLK/perfil/DVFS/histéresis | **effective frequency (duty cycle)** · **power domain** |
| `POWER` | cap/perfiles/energía/EDP | **validez del sensor** |
| `THERMAL` | constante/historia/deuda/recuperación | **ruido de medición** |
| `DRIVER` | Mesa stock/CUSTOM/versiones/workarounds/ICD | — |
| `MEASUREMENT` | sampling/overhead/observers/timestamps | **noise floor** · **control negativo** · **mining de artefactos** |

**Combinaciones no estudiadas con contradicción interesante:**
`WORKLOAD(multi-proceso) × QUEUE(arbitraje)` → contradice `AGENTS.md:347` (§11 `CON-01`)
`GPU-B × PCIe/host-memory/power` → aislaría confounds de **toda** medición existente
`SENSOR × WORKLOAD` → validity envelope en vez de valor
`TEXTURE-FILTER × SHADER(ILP)` → dos recursos distintos con la misma variable observable
`TLB × WORKING-SET` → mecanismo distinto al de bandwidth

---

## 5. MECANISMOS EXTERNOS

### 5.1 TRIZ (fuente verificada)
`EXTERNAL_KNOWLEDGE` · **Wikipedia "TRIZ"** · HTTP 200 · consultado 2026-09-27 ·
*"he developed a set of **40 inventive principles** and, later, a **matrix of
contradictions**"*; definición de **contradicción técnica**: *"optimizing one
parameter often leads to the deterioration of another"*.
**Uso:** generador de transformaciones. **NO** usado como prueba.

| PROBLEMA | CONTRADICCIÓN | PRINCIPIO | TRANSFORMACIÓN | IDEA |
|---|---|---|---|---|
| `P-02 MCLK forcing CONGELADO` vs `H7` necesita observar transiciones | contradicción **técnica**: autoriz. vs necesidad | **Sustitución mecánica** + **Intermediario** | en vez de escribir PM, **moldear el workload** para que el estado MCLK objetivo aparezca solo | `D2-12` |
| `OWNERSHIP=FULL` exige "sin cliente activo" vs `D2-06` necesita 2 clientes | contradicción **de requisito** | **Cambio a otra dimensión** | el criterio mide *aislamiento*; el objetivo necesita *concurrencia*: son **ejes distintos** | `NINGUNA` → se preserva como `CON-01` (§11) |
| La medición no tiene **piso** | contradicción *medida⇔fenómeno* | **Control negativo** | un workload de coste conocido que debe dar una lectura conocida | `D2-11` |
| `W_SMU` nunca validado | contradicción *métrica⇔magnitud* | **Intermediario** | medir la *forma* de la señal (rango, saturación, cadencia) en vez del valor | `D2-14` |
| 1321 artefactos sin revalidar | contradicción *evidencia⇔uso* | **Extracción** | minar lo ya capturado | `D2-10` |
| 5 resultados `NOT_AVAILABLE` sin pregunta derivada | vacío de medición | **Inversión** | la ausencia de un contador es en sí misma una variable | `D2-05`, `D2-04` |

### 5.2 DISEÑO POR ANALOGÍA (mecanismo abstracto, no solución)

| `DOMINIO_ORIGEN` | `MECANISMO_ABSTRACTO` | `POSIBLE_EQUIVALENTE_RX550` | IDEA | `EVIDENCIA` |
|---|---|---|---|---|
| CPU cache | reuse distance | presión de TLB en VRAM | `D2-05` | `EXTERNAL_KNOWLEDGE` |
| network congestion | queue buildup + latency cliff | construcción de cola GPU→WSI | `D2-16` *(demotida)* | `NOT_AVAILABLE` |
| thermal systems | path dependence | `R-NEW-61` ya lo tiene | — | corpus |
| OS scheduler | fairness / starvation | arbitraje de contextos GPU | `D2-06` | `EXTERNAL_KNOWLEDGE` |
| compiladores | early-exit / dead code | shaders nunca emitidos por rutas no cubiertas | **GAP_NO_IDEADO** | — |
| sistemas distribuidos | tail latency (p99 ≠ media) | `N-INT-41` ya lo tiene | — | corpus |
| métricas | sensor validity envelope | `power1_input` | `D2-14` | `EXTERNAL_KNOWLEDGE` |

### 5.3 LITERATURA TÉCNICA (verificada, `EXTERNAL_KNOWLEDGE`)

| Fuente | HTTP | Qué respalda | Límite |
|---|:--:|---|---|
| Wikipedia **Graphics Core Next** | 200 | Bloque SIMD GCN: *"4 **Texture Filter Units**, 16 **Texture Fetch Load/Store Units**, a 16 KiB level 1 (L1) cache, Four Compute Units"*, *"4 64 KiB VGPR files, 1 scalar unit (SU), 8 KiB scalar GPR file, a local data share of 64 KiB"* | `EXTERNAL_KNOWLEDGE`. El bloque citado es de GCN general; **no** verificado que RX550/Polaris12 tenga idéntico conteo |
| Wikipedia **TRIZ** | 200 | 40 principios + matriz de contradicciones; definición de contradicción técnica | `EXTERNAL_KNOWLEDGE` |
| Wikipedia **Morphological analysis** | 200 | página *stub*, sin contenido utilizable | **`PUBLICATION_DETAIL=NOT_AVAILABLE`** — el método se usó genéricamente |
| `https://gpuopen.com/amd-graphics-core-next-gcn/` | **404** | — | `NOT_AVAILABLE` |
| `https://www.vulkan.org/` · `docs.mesa3d.org/drivers/radv.html` | 200 | sin mecanismo nuevo extraíble | — |

> **Ninguna fuente externa convierte una idea en hecho sobre esta RX550.**

---

## 6. IDEAS GENERADAS

### 6.1 `GENUINELY_NEW` (16)

> Criterio: cada una difiere en ≥1 dimensión sustantiva frente a las 184.

#### `D2-01` — El **segundo GPU del host** como variable experimental

| Campo | Valor |
|---|---|
| `IDEA` | La RX550 siempre se ha medido con `renderD128`/`card0` (i915, GPU Kalm) activos en paralelo. Nunca se ha estudiado **si la actividad del segundo GPU altera** clocks, `W_SMU`, FPS oVRAM del RX550 (raíz PCIe compartida, ancho de banda de memoria de host, carril de alimentación).  |
| `GENERATION_METHOD` | FASE-1 `L` (anomalía) + FASE-2.8 (recursos no explotados) + FASE-2.5  |
| `MECHANISM` | **recombinación** + **cambio de contexto**  |
| `CORPUS` | `R1-20260926T030435Z.json` (`renderD128`+`card0` con 9+9 FDs, `renderD129`+`card1` con 9+9) · `AGENTS.md:38-41` (3 identidades de host) · `DOCUMENTATION-CENSUS.md:178` §5  |
| `RELATION` | **ninguna** de las 184  |
| `QUESTION` | ¿La presencia y carga del segundo GPU es un confound activo en todas las mediciones previas?  |
| `HYPOTHESIS_SEED` | *ninguna escrita* (regla: no crear hipótesis automáticamente)  |
| `INDEPENDENT_VARIABLE` | carga del segundo GPU (0 / ligera / pesado)  |
| `DEPENDENT_VARIABLE` | SCLK, MCLK, `W_SMU`, FPS, `drm_fds_found`  |
| `DISCRIMINANT` | Si la carga del segundo GPU **no** cambia nada ⇒ el recurso compartido no es limitante y las mediciones previas son válidas. Si cambia ⇒ **todos** los resultados anteriores están contaminados  |
| `EVIDENCE` | `EXTERNAL_KNOWLEDGE` (mismo board, 2 GPUs, ver `R1`)  |
| `MISSING` | inventario de uso del segundo GPU; ancho de banda compartido  |
| `BLOCKERS` | ninguno técnico. Requiere medir el otro GPU, que es material de otro proyecto  |
| `RISK` | **ALTO** si resulta positivo: invalidaría resultados previos. Bajo si negativo  |

#### `D2-02` — **Piso de ruido** y repetibilidad de la cadena de medición

| Campo | Valor |
|---|---|
| `IDEA` | Caracterizar la varianza run-to-run de la cadena completa (W_SMU, SCLK, MCLK, FPS, frametime) a condiciones fijas, para obtener el **piso de ruido** y el **tamaño de efecto mínimo detectable**.  |
| `GENERATION_METHOD` | FASE-2.4 (descomposición) + FASE-2.10 (medicación) + FASE-2.11 (escala) + TRIZ *control negativo*  |
| `MECHANISM` | **descomposición** + **cambio de contexto**  |
| `CORPUS` | `R-NEW-94/95/96/97/98` (acuerdo entre observadores, latencia, sampling, overhead, timestamps) — **ninguno** mide repetibilidad  |
| `RELATION` | `VARIANT_OF` el *vecindario* (`R-NEW-94..98`), pero **nueva** en dimensión *escala=entre-runs* y en *propósito=precondición de inferencia*  |
| `QUESTION` | ¿Cuál es el mínimo efecto real que este host puede detectar?  |
| `INDEPENDENT_VARIABLE` | ninguna variable física; se repite el mismo workload N veces  |
| `DEPENDENT_VARIABLE` | dispersión de W_SMU/SCLK/MCLK/FPS/frametime  |
| `DISCRIMINANT` | Si σ es grande frente a los efectos esperados por `H1..H12`, **varias hipótesis son indecidables con este instrumento**  |
| `EVIDENCE` | `NOT_AVAILABLE`  |
| `MISSING` | n y varianza de las corridas existentes  |
| `BLOCKERS` | ninguno (lectura, sin escritura)  |
| `RISK` | bajo. Alto valor de descarte: puede cerrar líneas por no-decidibilidad  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-03` — **Filtrado de textura** como familia de variables

| Campo | Valor |
|---|---|
| `IDEA` | El corpus no tiene ninguna idea sobre muestreo de textura: filtrado anisotrópico, trilineal, selección de mip/LOD, sesgo de LOD, estado de sampler, número de taps. GCN tiene hardware dedicado de filtrado y de fetch **separado** del shader.  |
| `GENERATION_METHOD` | FASE-2.8 (recursos) + FASE-1 `C` + `EXTERNAL_KNOWLEDGE`  |
| `MECHANISM` | **transferir** (mecanismo de textura a la pregunta) + **descomponer**  |
| `CORPUS` | `EXTERNAL_KNOWLEDGE`: bloque SIMD GCN con *"4 Texture Filter Units"* y *"16 Texture Fetch Load/Store Units"* separados de los Compute Units. En el corpus de ideas: 0 ocurrencias de `aniso`, `trilinear`, `mip`, `LOD bias`, `texture filter`  |
| `RELATION` | `G-01..G-08` estudian geometría/raster; ninguna toca el采样 texture. **ninguna** relación  |
| `QUESTION` | ¿El filtrado de textura es un recurso limitante distinto del bandwidth de textura?  |
| `INDEPENDENT_VARIABLE` | modo de filtrado (nearest/bilinear/trilinear/aniso 1×2×4×8×16), sesgo de LOD, nº de mips  |
| `DEPENDENT_VARIABLE` | FPS, frametime, `shader_busy`, `mem_busy`, W_SMU  |
| `DISCRIMINANT` | Si subir anisotropía **no** cambia nada mientras el bandwidth sí ⇒ son recursos separados; si ambos escalan juntos ⇒ mismo cuello  |
| `EVIDENCE` | `EXTERNAL_KNOWLEDGE` (GCN)  |
| `MISSING` | conteo real de TFU en Polaris12; comportamiento de RADV con samplers  |
| `BLOCKERS` | ninguno  |
| `RISK` | medio: el corpus ya tiene `G-*` de alta prioridad; añadir una familia más compite por recursos de experimentación  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-04` — **LDS / banco compartido** y conflictos de banco

| Campo | Valor |
|---|---|
| `IDEA` | El corpus estudia la divergencia de accesos **dentro de un wave a memoria global** (`N-INT-10`). No estudia el **LDS** (local data share) ni los **conflictos de banco**, que son una unidad, un hardware y un coste distintos.  |
| `GENERATION_METHOD` | FASE-2.1 (analogía con cache-line/bank) + FASE-2.8  |
| `MECHANISM` | **analogía** (patrón de acceso conflictivo en cachelines ⇄ bancos LDS)  |
| `CORPUS` | `EXTERNAL_KNOWLEDGE`: *"a local data share of 64 KiB"* y *"8 KiB scalar GPR file"* en el bloque SIMD GCN. Corpus de ideas: `LDS`=0, `shared memory`=0, `bank conflict`=0  |
| `RELATION` | `VARIANT_OF(N-INT-10)` en familia memoria, pero **mecanismo distinto** (LDS vs VMEM; banco vs cacheline)  |
| `QUESTION` | ¿La Conflicts LDS es un cuello medible y distinto del de bandwidth?  |
| `INDEPENDENT_VARIABLE` | patrón de índice LDS (broadcast vs 2-bancos vs N-bancos)  |
| `DEPENDENT_VARIABLE` | FPS, `shader_busy`  |
| `DISCRIMINANT` | Mismo número de accesos, distinto patrón de banco ⇒ si el coste cambia, el mecanismo es el banco  |
| `EVIDENCE` | `EXTERNAL_KNOWLEDGE` (GCN)  |
| `MISSING` | banco por acceso en GFX8; contador de LDS  |
| `BLOCKERS` | contador de LDS = `NOT_AVAILABLE` (PMU GFX8) ⇒ sólo vía frametime  |
| `RISK` | medio-alto: sin contador, la atribución es indirecta  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-05` — **TLB y page size**

| Campo | Valor |
|---|---|
| `IDEA` | El corpus trata la memoria sólo como *bandwidth* y como *working set*. No hay ninguna idea sobre el **TLB** (jerarquía de traducción) ni sobre el **tamaño de página** de VRAM/host. Un cambio de page size cambia el número de traducciones sin cambiar los bytes transferidos.  |
| `GENERATION_METHOD` | FASE-2.8 (recursos) + analogía de TLB de CPU  |
| `MECHANISM` | **transferir** (mismo mecanismo: caché de traducciones)  |
| `CORPUS` | `TLB`=0, `page size`=0, `hugepage`=0, `NUMA`=0 en las 184. `H6`/`M-01`/`R-NEW-41` son *bandwidth/working set*  |
| `RELATION` | `VARIANT_OF(H6)` en la línea de memoria, pero **variable independiente distinta** (páginas, no bytes) y **mecanismo distinto**  |
| `QUESTION` | ¿La RX550 es sensible a la traducción (TLB) antes que al bandwidth?  |
| `INDEPENDENT_VARIABLE` | page size de VRAM y de host; working set constante  |
| `DEPENDENT_VARIABLE` | FPS, `mem_busy`, `shader_busy`  |
| `DISCRIMINANT` | working set **constante** y sólo cambia page size ⇒ si el coste cambia, no es bandwidth  |
| `EVIDENCE` | `NOT_AVAILABLE`  |
| `MISSING` | jerarquía TLB de GFX8; control del page size por software  |
| `BLOCKERS` | **posible**: cambiar page size de VRAM puede requerir privileged. **Determinar**  |
| `RISK` | medio. Puede acabar bloqueada, pero vale la pena intentarlo en modo lectura  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-06` — **Arbitraje multi-proceso** y contención entre contextos

| Campo | Valor |
|---|---|
| `IDEA` | El corpus es casi enteramente *single-workload, single-proceso*. `O-P0-ENV` y los documentos de ownership tratan a los clientes como **contaminación** a aislar, no como **variable**. La pregunta «cómo arbitra la GPU entre 2 contextos» no está en ninguna de las 184.  |
| `GENERATION_METHOD` | FASE-2.5 (recombinación: `WORKLOAD × QUEUE`) + analogía de OS scheduler + FASE-3  |
| `MECHANISM` | **analogía** (fairness/starvation de scheduler) + **recombinación**  |
| `CORPUS` | `O-P0-ENV` (clientes a aislar) · `H8` (starvation de un solo cliente) · `H9`/`A-01` (async overlap, mismo proceso)  |
| `RELATION` | **ninguna** de las 184  |
| `QUESTION` | ¿Cuál es la política de arbitraje y time-slice entre 2 procesos, y qué le pasa a la latencia de cada uno?  |
| `INDEPENDENT_VARIABLE` | presencia y carga de un 2º proceso  |
| `DEPENDENT_VARIABLE` | FPS y frametime de **ambos** procesos; clocks; W_SMU  |
| `DISCRIMINANT` | 1 proceso vs 2 procesos a carga total constante ⇒ ¿suma lineal (compartición justa) o sub-lineal (overhead de cambio de contexto)?  |
| `EVIDENCE` | `OBSERVED` parcial: `R1` muestra 12 clientes y 2 GPUs simultáneos  |
| `MISSING` | política de time-slice; latencia de conmutación  |
| `BLOCKERS` | **`CON-01`**: contradice `AGENTS.md:347` (`OWNERSHIP != FULL` si «a client is active»). La investigación requiere exactamente lo que el criterio prohíbe  |
| `RISK` | **ALTO**: no es sólo autorización, es una contradicción de requisito del proyecto  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-07` — **Preemption** de compute (sub-mecanismo de `D2-06`)

`SUBIDEA(D2-06)` · no se cuenta como `GENUINELY_NEW` · VMNI/preemption dentro del mismo proceso es un mecanismo distinto al arbitraje entre procesos, pero comparte observable (latencia) y bloqueador (`CON-01`).

#### `D2-08` — **Asimetría de dominios de energía** (graphics vs memory)

| Campo | Valor |
|---|---|
| `IDEA` | `R-NEW-51` pregunta por **independencia de frecuencias** SCLK/MCLK. Esto pregunta por **dominios de energía**: ¿el draw del dominio de memoria sigue activo cuando el de gráficos idle, y viceversa? Es otro recurso y otro observable (corriente cuando un dominio idle).  |
| `GENERATION_METHOD` | FASE-2.8 (recurso) + FASE-2.4  |
| `MECHANISM` | **descomponer** (dividir «clock» en dominio-clock y dominio-energía)  |
| `CORPUS` | `R-NEW-51` (independencia de relojes) · `H7`/`P-01` (DPM/power). Dominio de energía = **0** ocurrencias  |
| `RELATION` | `VARIANT_OF(R-NEW-51)` — pero **recurso distinto** (dominio vs reloj)  |
| `QUESTION` | ¿Hay gating asimétrico de dominios que el DPM de reloj no revela?  |
| `INDEPENDENT_VARIABLE` | workload que ejercita sólo un dominio  |
| `DEPENDENT_VARIABLE` | W_SMU, clocks, current draw  |
| `DISCRIMINANT` | Carga sólo-graphics vs sólo-memoria vs ambas: si W_SMU no baja en el caso sólo-graphics, hay coste fijo  |
| `EVIDENCE` | **`NOT_AVAILABLE`** — no verifiqué que GCN exponga dominios de energía separables  |
| `MISSING` | verificación de la existencia del mecanismo en GFX8  |
| `BLOCKERS` | ninguno para observar; ninguno para intervenir  |
| `RISK` | medio: si el mecanismo no existe, es una idea vacía. **Requiere verificación previa**  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-09` — Estimador de **frecuencia efectiva** por ciclo de trabajo

| Campo | Valor |
|---|---|
| `IDEA` | El corpus registra `frequency_effective_estimate=NOT_AVAILABLE` como **hueco del claim B de C1** (`02-HIPOTESIS-H1-H12.md`, tabla claims). **Ninguna idea propone cómo obtenerlo.** Consiste en derivar la frecuencia efectiva como promedio ponderado por *duty cycle* a partir de la distribución de estados de reloj ya preservada en los artefactos.  |
| `GENERATION_METHOD` | FASE-2.10 (métrica insuficiente → variable latente) + FASE-2.9 (inversión de `NOT_AVAILABLE`)  |
| `MECHANISM` | **invertir** (`NOT_AVAILABLE` → estimador)  |
| `CORPUS` | `02-HIPOTESIS-H1-H12.md` claim B `frequency_effective_estimate=NOT_AVAILABLE` · `…ADDENDUM` 5 capas  |
| `RELATION` | `DERIVES_FROM` el hueco documentado; **no** relación con las 184  |
| `QUESTION` | ¿Se puede reconstruir la frecuencia efectiva a posteriori de las corridas preservadas?  |
| `INDEPENDENT_VARIABLE` | ventana temporal, ponderación por permanencia en cada estado  |
| `DEPENDENT_VARIABLE` | frecuencia efectiva estimada vs clock instantáneo  |
| `DISCRIMINANT` | Si la freq. efectiva calculada predice el `shader_busy` preservado y el instantáneo no ⇒ el clock instantáneo es la métrica engañosa  |
| `EVIDENCE` | `OBSERVED`: los artefactos preservados contienen distribuciones de SCLK/MCLK (`R1-024340Z`, `R1-030435Z`)  |
| `MISSING` | verificar que la distribución por estado está realmente en los artefactos  |
| `BLOCKERS` | ninguno (post-proceso)  |
| `RISK` | **ALTO**: una métrica mal definida se propaga a todas las conclusiones que la usen  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-10` — **Minar los artefactos preservados** en vez de ejecutar nuevas corridas

| Campo | Valor |
|---|---|
| `IDEA` | `DOCUMENTATION-CENSUS.md:284`: *«Veracidad de las afirmaciones de los 1321 artefactos de medición. **No se revalidó ninguna cifra**; se clasificó su función, no su corrección»*. **Ninguna idea propone analizar lo ya capturado.** Incluye: distribuciones de reloj intra-run, `maps` por proceso, tiempo de escaneo por PID, y el contraste entre las 2 corridas de collector (una falló con `KeyError`/`UnboundLocalError`, la otra no).  |
| `GENERATION_METHOD` | FASE-2.8 (recurso no explotado) + FASE-2.10 + FASE-2.11  |
| `MECHANISM` | **extracción** (TRIZ) + **cambio de contexto**  |
| `CORPUS` | `DOCUMENTATION-CENSUS.md:284` · `R1-024340Z` (`KeyError: 'total_pid…'`) · `R1-030435Z` (`8806311b`) · `/tmp/opencode/hd06/GROUPS.json`  |
| `RELATION` | **ninguna** de las 184  |
| `QUESTION` | ¿Cuántas preguntas ya respondidas no lo saben?  |
| `INDEPENDENT_VARIABLE` | qué artefacto y qué variable se extrae  |
| `DEPENDENT_VARIABLE` | distribución temporal de clocks; coste por PID; unidad de `active_gpu_clients`  |
| `DISCRIMINANT` | Si una distribución preservada muestra una transición de clock no vista en el informe ⇒ el informe estaba incompleto, no el artefacto  |
| `EVIDENCE` | `OBSERVED`: los artefactos existen y están preservados  |
| `MISSING` | índice de qué variable hay en qué artefacto  |
| `BLOCKERS` | **ninguno**: es post-proceso, sólo lectura, **sin autorización especial**  |
| `RISK` | **MUY BAJO** y **valor muy alto**: es la única familia de ideas de esta ronda ejecutable sin autorización  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-11` — **Workloads de control negativo / calibración** del instrumento

| Campo | Valor |
|---|---|
| `IDEA` | `TESTING.md §2` tiene pruebas negativas para la *herramienta de contrato del host*, pero no hay **workloads de calibración** para la cadena de medición de la GPU: un blit puro (debe ser 100% bandwidth-present), un shader de coste analítico conocido, un compute puro sin present. Sirven para **verificar que el instrumento responde como se predice antes de usarlo para comparar**.  |
| `GENERATION_METHOD` | FASE-2.10 + TRIZ *control negativo* + analogía de calibración de instrumentos  |
| `MECHANISM` | **combinar** (validación de instrumento)  |
| `CORPUS` | `TESTING.md:24` §2 (pruebas negativas del host) · `EXPERIMENT-CANDIDATES.md` (no incluye calibración) · `R-14..R-18` «control negativo» ya existe como concepto en `TESTING.md §5` (MIG-07.9 R-8)  |
| `RELATION` | `DERIVES_FROM` un concepto ya existente, aplicado a un dominio nuevo  |
| `QUESTION` | ¿El instrumento mide lo que dice medir?  |
| `INDEPENDENT_VARIABLE` | workload de calibración  |
| `DEPENDENT_VARIABLE` | lectura esperada vs medida  |
| `DISCRIMINANT` | Si blit puro no da 100% del clock esperado, la cadena de medición está mal calibrada y **ningún** resultado previo es interpretable  |
| `EVIDENCE` | `NOT_AVAILABLE`  |
| `MISSING` | definición de las lecturas esperadas  |
| `BLOCKERS` | ninguno de escritura; requiere ejecutar workloads GPU (**autorización**, fuera de esta tarea)  |
| `RISK` | bajo; valor de descarte alto  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-12` — **Moldear el workload** en vez de forzar el registro de clocks/power

| Campo | Valor |
|---|---|
| `IDEA` | `P-02` (MCLK forcing) y `P-03` (heating) están `CONGELADO` porque requieren escribir sysfs/riesgo térmico. Existe una vía **sin autorización**: diseñar workloads que **produzcan naturalmente** el estado de reloj o la carga térmica objetivo, y observar. Convierte un bloqueo de autorización en un problema de diseño de workload.  |
| `GENERATION_METHOD` | FASE-2.2 (inversión: en vez de forzar el estado, producirlo) + TRIZ *sustitución mecánica* + *intermediario*  |
| `MECHANISM` | **invertir** + **transferir**  |
| `CORPUS` | `P-02` `CONGELADO` (`EXPERIMENT-CANDIDATES.md:283`) · `P-03` `CONGELADO` (:291) · `R-NEW-41` (working-set ladder, que **ya usa esta vía** para VRAM) · `R-NEW-47` («forma menos peligrosa de H7»)  |
| `RELATION` | `VARIANT_OF(R-NEW-41)` extendido a clocks/power; **nuevo** en `recurso estudiado` (diseño de workload en vez de registro PM) y en `método`  |
| `QUESTION` | ¿Se puede llevar la GPU a cualquier estado de reloj/thermal objetivo sólo con carga?  |
| `INDEPENDENT_VARIABLE` | workload diseñado (presión de memoria, ALU, textura)  |
| `DEPENDENT_VARIABLE` | estado de clock/thermal alcanzado  |
| `DISCRIMINANT` | Si la workload alcanza el estado objetivo sin escribir ⇒ `P-02`/`H7` dejan de estar bloqueados  |
| `EVIDENCE` | `OBSERVED` parcial: `R-NEW-41` ya usa la vía para VRAM (`OBSERVED` que la escalera working-set mueve presión)  |
| `MISSING` | mapa workload → estado de reloj  |
| `BLOCKERS` | ninguno de escritura; ejecutar el workload requiere autorización  |
| `RISK` | **MUY BAJO**: no escribe nada. Es la vía más promisoria para desbloquear `H7`  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-13` — Envolvente de **validez del sensor** de `power1_input`

| Campo | Valor |
|---|---|
| `IDEA` | Todo el corpus dice «`W_SMU` es estimador, no vatímetro», pero **ninguna idea propone caracterizar el estimador**: ¿en qué rango es lineal?, ¿satura?, ¿cuál es su cadencia de actualización?, ¿con qué resolución? Sin esa envolvente no se puede saber si una comparación de 9,4 vs 13,6 W significa nada.  |
| `GENERATION_METHOD` | FASE-2.9 (negativo: el sensor es insuficiente) + FASE-2.10 + TRIZ *intermediario*  |
| `MECHANISM` | **invertir** (de «leer un valor» a «validar el instrumento»)  |
| `CORPUS` | `KNOWLEDGE-POLICY` y todo el corpus: `W_SMU` ≠ vatímetro (límite repetido) · `02-ARQUITECTURA/evidence.md:3` (nota de trazabilidad)  |
| `RELATION` | `VARIANT_OF(R-NEW-99)` (mapa semántico de métricas) — pero aplicado al **sensor** y con pregunta distinta  |
| `QUESTION` | ¿Cuál es la envolvente de validez del estimador que sostiene la mayor parte de las cifras del proyecto?  |
| `INDEPENDENT_VARIABLE` | carga conocida que barre un rango amplio  |
| `DEPENDENT_VARIABLE` | lectura de `power1_input` vs referencia conocida  |
| `DISCRIMINANT` | Si la lectura **no** responde a la carga en un tramo, ese tramo es indistinguible de 0 y toda comparación ahí es inválida  |
| `EVIDENCE` | `NOT_AVAILABLE`  |
| `MISSING` | especificación del sensor SMU; alguna lectura de referencia  |
| `BLOCKERS` | ninguno de escritura para observar; referencia externa haría falta  |
| `RISK` | medio: puede revelar que diferencias documentadas son ruido  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-14` — Divergencia **replay vs retirement** en SQ

| Campo | Valor |
|---|---|
| `IDEA` | En GCN el SQ emite *allocations* que pueden ser **replay**. Una idea sobre instrucción ejecutada debe distinguir *emitida* de *retirada*. Ninguna de las 184 lo hace; `Q1..Q7` cuentan eventos de ciclo, noIssued-vs-retired.  |
| `GENERATION_METHOD` | FASE-2.8 (recurso: SQ)  |
| `MECHANISM` | **descomponer** (ejecución = issued ⊎ replay ⊎ retired)  |
| `CORPUS` | `FASE-D-ETAPA-3-PLAN.md:69-98` (inventario de contadores; `SQ_PERFCOUNTER0–15` marcado `C` por requerir ventana de shader)  |
| `RELATION` | `VARIANT_OF(Q2)` — pero con una variable que el plan no propone  |
| `QUESTION` | ¿Cuánto del trabajo emitido no se retira?  |
| `INDEPENDENT_VARIABLE` | workload con predicción de ramas divergentes  |
| `DEPENDENT_VARIABLE` | issued vs retired  |
| `DISCRIMINANT` |issued≫retired ⇒ la métrica actual de "shader ocupado" cuenta trabajo que no se completa |
| `EVIDENCE` | `NOT_AVAILABLE`  |
| `MISSING` | semántica exacta de los contadores de retirement en GFX8  |
| `BLOCKERS` | **`BLOQUEADA`**: selectores GFX8 prohibidos (`…ADDENDUM:104`); contadores windowed requieren `SQ_PERFCOUNT_WINDOWED`  |
| `RISK` | medio-alto. Registrable como idea, **no** como línea ejecutable hoy  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |
| `DISCRIMINANT` | `NOT_DETERMINED` |

#### `D2-15` — **Migración de cuello de botella** como Searches sobre el corpus preservado

| Campo | Valor |
|---|---|
| `IDEA` | `N-INT-61` propone la migración como *bucle de una corrida*. Lo noOSED es aplicarlo **entre corporos**: el régimen histórico (`O-ROOT`, 25-31 W) y el estado actual (≤13,6 W) pueden tener **cuellos de botella distintos**, y la comparación sería evidencia de migración sin ejecutar nada.  |
| `GENERATION_METHOD` | FASE-2.13 (migración) + FASE-2.9 (negativo: `O-ROOT` sin causa)  |
| `MECHANISM` | **migración de cuello**  |
| `CORPUS` | `O-ROOT` (`Causa [DESCONOCIDA]`, `[NO REPRODUCIBLE]`) · `N-INT-61` · `R-01..R-09` (9 refutaciones)  |
| `RELATION` | `REFORMULA(N-INT-61)` sobre evidencia existente; `CONTRADICTS` con el cierre de `O-ROOT` («sin autorización nueva NO se investiga más»)  |
| `QUESTION` | ¿Cambió el cuello de botella entre el régimen histórico y hoy?  |
| `INDEPENDENT_VARIABLE` | corpus histórico vs actual  |
| `DEPENDENT_VARIABLE` | posición del cuello identificado  |
| `DISCRIMINANT` | Si los 9 refutados siguen refuteando hoy, el cuello **no** migró; si alguno ya no aplica, migró  |
| `EVIDENCE` | `NOT_AVAILABLE` (falta el corpus histórico comparable)  |
| `MISSING` | datos del régimen 17/09 con la misma instrumentación  |
| `BLOCKERS` | **`O-ROOT` cerrado por decisión humana.** Registrar, no ejecutar  |
| `RISK` | — (no se ejecuta)  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |

#### `D2-16` — **Líneas base de referencia** para cualquier afirmación de mejora

| Campo | Valor |
|---|---|
| `IDEA` | El corpus mide differentially (EP-05 CUSTOM vs STOCK, FASE-D A vs B) pero **no tiene una línea base absoluta** calibrada: un blit, un triangle, un compute puro con coste analítico. Sin base, un 73 FPS no dice si es alto o bajo para esta placa.  |
| `GENERATION_METHOD` | FASE-2.10 + analogía de calibración  |
| `MECHANISM` | **descomponer** (separar «rendimiento absoluto» de «rendimiento relativo»)  |
| `CORPUS` | `EXPERIMENT-CANDIDATES.md:305-315` (variables de control fijas) — fija constantes pero **no** valores de referencia  |
| `RELATION` | `DERIVES_FROM(D2-11)`; **nueva** en `propósito` (escala absoluta vs relativa)  |
| `QUESTION` | ¿Cuál es el techo y el suelo de esta placa en condiciones definidas?  |
| `INDEPENDENT_VARIABLE` | workload trivial definido  |
| `DEPENDENT_VARIABLE` | FPS/frametime/W_SMU  |
| `DISCRIMINANT` | Techo declarado (memoria) vs observado ⇒ distancia al techo con criterio  |
| `EVIDENCE` | `NOT_AVAILABLE`  |
| `MISSING` | valores de referencia publicados para GFX8  |
| `BLOCKERS` | autorización de workload  |
| `HYPOTHESIS_SEED` | `NOT_DETERMINED` (no redactada: no crear hipótesis automáticamente) |
| `RISK` | `NOT_DETERMINED` |

### 6.2 `VARIANT_OF` / `DUPLICATE_OF` / `SUBIDEA` / `ALREADY_COVERED` — 45 candidatas demotadas

| Candidata | Veredicto | Motivo |
|---|---|---|
| doorbell→inicio de trabajo | `VARIANT_OF(R-NEW-25)` | misma línea temporal submit→fence; distinto punto medio |
| p99 entre corridas | `VARIANT_OF(R-NEW-96)` | sampling/overhead ya cubiertos |
| segunda workload para ceilings | `ALREADY_COVERED` | `EXPERIMENT-CANDIDATES` ya tiene 23 candidatos multi-workload |
| `D2-D3` segundo proceso para medir concurrencia | `DUPLICATE_OF(R-NEW-83,H10)` | comparación por workload ya existe |
| forzar MCLK con cap bajo para evitar cuelgue | **NO ES IDEA** | es una * mitigación de seguridad* de un experimento bloqueado, no una pregunta |
| trazar fd→nodo para atribuir clientes | `ALREADY_COVERED` | es el trabajo `R1`/attributable completo |
| clocks por proceso vía `/proc` | `NOT_DETERMINED` | bloqueado por permisos y **no abre pregunta nueva** |
| texture LOD como variable separada | `SUBIDEA(D2-03)` | mismo recurso, misma variable observable |
| aniso como barrido numérico | `SUBIDEA(D2-03)` | cambia parámetro, no mecanismo |
| descriptor set update batching | `DUPLICATE_OF(N-INT-33/34/50)` | — |
| replay como métrica sin contadores | `NOT_DETERMINED` | sin dato, no es idea ejecutable |
| +L0 de las 41 restantes | `VARIANT_OF` / `DUPLICATE_OF` de familias existentes | ver detalle abajo |

| Familia candidata | Veredicto consolidado |
|---|---|
| `VBO/IBO + patrón de acceso` (4) | `DUPLICATE_OF(R-NEW-07, G-03)` |
| `draw/batch/descriptor/pipeline` densidades (6) | `DUPLICATE_OF(R-NEW-13, N-INT-35/36, R-NEW-92/93)` |
| `perfil × workload` (3) | `DUPLICATE_OF(R-NEW-104..107, P-01)` |
| `lDS sizing/workgroup` (2) | `VARIANT_OF(R-NEW-68, S-01)` —Vecino, no nuevo |
| `texture cache / reuse distance` (3) | `VARIANT_OF(N-INT-16..18)` en familia memoria |
| `histéresis en clocks` (3) | `DUPLICATE_OF(H7, R-NEW-47/49, N-INT-60)` |
| `métrica de energía` (3) | `DUPLICATE_OF(R-NEW-56, N-INT-58/59)` |
| `frecuencia por workload class` (2) | `DUPLICATE_OF(N-INT-57, H1)` |
| `preempt` (1) | `SUBIDEA(D2-06)` |
| `TLS/Texture-only` (2) | `SUBIDEA(D2-03)` |
| `recovery / teardown de frame` (2) | `VARIANT_OF(N-INT-39)` |
| `overdraw × Early-Z` (2) | `DUPLICATE_OF(G-05, N-INT-21/22)` |
| `async interference` (2) | `DUPLICATE_OF(A-01, N-INT-45..47)` |
| `pipeline/shader cache` (2) | `DUPLICATE_OF(R-NEW-69, N-INT-37/38)` |
| `buffer packing` (2) | `DUPLICATE_OF(M-03, N-INT-49)` |

### 6.3 Ataque adversarial — tasa de rechazo
**67 candidatas generadas → 15 sobreviven (22 %)**  · 52 demotadas = 26 `DUPLICATE_OF` + 22 `VARIANT_OF` + 4 `SUBIDEA`
(varias candidatas no se generaron: 3 del §6.2 se descartaron como `NOT_AN_IDEA` antes de numerarse). Criterios que más rechazaron:
`¿Es simplemente cambiar un parámetro?` (21) · `¿Es una variante?` (14) · `¿La evidencia ya la cubre?` (7) · `¿Confunde instrumento con fenómeno?` (3) — las 3 descartadas eran métricas propuestas como线的 nuevas.

---

## 7. `DUPLICATE_OF` — 9 filas · 26 candidatas

> **Unidad:** una *fila* puede agregar varias candidatas; el agregado va en `(n)`.
> Las 10 filas sueltas del §6.2 están consolidadas aquí y **no se suman dos veces**.

| Candidata | Descripción | `DUPLICATE_OF` | Motivo |
|---|---|---|
| `D2-d1` | medir concurrencia con 2º proceso | `R-NEW-83`,`H10` | comparación por workload ya existe |
| `D2-d2` | VBO/IBO × patrón de acceso (4) | `R-NEW-07`,`G-03` | `G-03` ya barre tamaño de buffer |
| `D2-d3` | densidad de draws/descriptors/pipeline-state (6) | `R-NEW-13`,`R-NEW-92`,`R-NEW-93`,`N-INT-35`,`N-INT-36` | corpus ya los tiene |
| `D2-d4` | perfil × workload (3) | `R-NEW-104..107`,`P-01` | — |
| `D2-d5` | histéresis de clocks (3) | `H7`,`R-NEW-47`,`R-NEW-49`,`N-INT-60` | — |
| `D2-d6` | métricas de energía (3) | `R-NEW-56`,`N-INT-58`,`N-INT-59` | — |
| `D2-d7` | Async interference (2) | `A-01`,`N-INT-45..47` | — |
| `D2-d8` | pipeline/shader cache cold-warm (2) | `R-NEW-69`,`N-INT-37/38` | — |
| `D2-d9` | buffer packing / per-object vs batched (2) | `M-03`,`N-INT-49/50` | — |

## 8. `VARIANT_OF` — 10 filas · 22 candidatas

| Candidata | Descripción | `VARIANT_OF` | Dimensión que cambia |
|---|---|---|
| `D2-v1` | doorbell → inicio de trabajo | `R-NEW-25` | punto medio de la línea temporal |
| `D2-v2` | p99 entre corridas | `R-NEW-96` | escala entre-runs |
| `D2-v3` | p99 / autocorrelación como métrica | `N-INT-41/42` | escala |
| `D2-v4` | LDS sizing / workgroup size (2) | `R-NEW-68`,`S-01` | recurso (LDS) |
| `D2-v5` | texture cache / reuse distance (3) | `N-INT-16..18` | mecanismo de caché |
| `D2-v6` | frecuencia por workload class (2) | `N-INT-57`,`H1` | clasificador |
| `D2-v7` | recovery / teardown de frame (2) | `N-INT-39` | dominio temporal |
| `D2-v8` | overdraw × Early-Z (2) | `G-05`,`N-INT-21/22` | orden de primitivas |
| `D2-v9` | sincronización: barrier scope/stage/access (7) | `A-01`,`N-INT-26..32` | granularidad de máscara |
| `D2-v10` | line base | `D2-11` | escala del objetivo |

## 9. `SUBIDEA` — 4 filas · 4 candidatas

| Candidata | Descripción | `PARENT_ID` | Motivo |
|---|---|---|
| `D2-07` | Preemption de compute dentro del proceso | `D2-06` | mismo observable (latencia) y mismo bloqueador (`CON-01`), mecanismo distinto |
| `D2-03b` | Selección de LOD/mip como variable separada | `D2-03` | mismo recurso y misma variable observable; cambia el parámetro, no el mecanismo |
| `D2-03c` | Nº de taps anisotrópicos como barrido numérico | `D2-03` | barrido de magnitud sobre la misma variable; no abre pregunta nueva |
| `D2-11b` | Workload de calibración de un driver concreto | `D2-11` | caso particular del mismo método de calibración |

## 10. `GENUINELY_NEW` = **15**

> `D2-07` **no** se cuenta aquí: es `SUBIDEA(D2-06)`. Los 16 encabezados `####` del §6.1 son 15 `GENUINELY_NEW` + 1 subidea.

`D2-01` segundo GPU · `D2-02` piso de ruido · `D2-03` filtrado de textura · `D2-04` LDS/bancos · `D2-05` TLB/page size · `D2-06` arbitraje multi-proceso · `D2-08` dominios de energía · `D2-09` frecuencia efectiva · `D2-10` minar artefactos · `D2-11` control negativo · `D2-12` moldear workload · `D2-13` validez del sensor · `D2-14` replay/retirement · `D2-15` migración entre corpus · `D2-16` línea base absoluta

## 11. `CONTRADICTIONS_WITHOUT_IDEA` (3 — ninguna idea las resuelve)

| ID | Afirmación A | Afirmación B | Scope | Tipo | Por qué **ninguna idea** lo resuelve |
|---|---|---|---|---|---|
| `CON-01` | `AGENTS.md:347`: `OWNERSHIP != FULL` si «a client is active» | `D2-06` requiere un 2º cliente activo para estudiar arbitraje | proyecto | **contradicción de requisito** | la contradicción es entre el *criterio de measurement* y el *objeto de investigación*. Requiere decisión humana: ¿el criterio de ownership aplica a la investigación de arbitraje? No hay transformación que lo evite sin falsear el criterio |
| `CON-02` | `AGENTS.md:337-344` + `R1-030435Z`: la RX550 **nunca** está idle (`kwin_wayland` con 9 FDs en `renderD129`) | `OWNERSHIP=FULL` exige aislamiento | proyecto | **condición insatisfacible en el estado real** | el criterio describe un estado que el host real no alcanza. `D2-01` lo *muestra* pero no lo arregla. Requiere decisión humana sobre si `FULL` es alcanzable en producción o sólo en un host dedicado |
| `CON-03` | `FASE-D-ETAPA-3-PLAN`: Q1–Q7 dependen de contadores programados | `…ADDENDUM:104`: programación GFX8 «prohibida por ahora» | fase | **plan vs prohibición** | ya registrada en el corpus; ninguna idea la resuelve. Requiere decisión sobre capability/prohibición |

**Registro explícito:** ninguna de las 3 se "resuelve" con una idea. Se preservan.

## 12. `GAPS_SIN_IDEA` (9)

| ID | Hueco | Por qué ninguna idea lo cubre |
|---|---|---|
| `GAP-01` | **firmware / vBIOS / PSP / fuses** | explícitamente fuera de alcance (`FASE-D-ETAPA-3-PLAN:66`). No verifiqué qué hay. `LIMITATION` |
| `GAP-02` | **motor de scanout / underrun** | requeriría investigar WSI a nivel de display engine, fuera del corpus. `NOT_DETERMINED` |
| `GAP-03` | **multi-monitor / multi-display** | el host tiene 1 display documentado; no hay corpus. `NOT_AVAILABLE` |
| `GAP-04` | **escala de instrucción** (no hay ninguna idea a escala de instrucción) | el corpus lowest-level es el shader. `GAP_NO_IDEADO` honesto |
| `GAP-05` | **interacción con la segunda GPU por PCIe Specifically** | `D2-01` lo cubre en general, no descompuesto por raíz PCIe |
| `GAP-06` | **VC/virtualización de GPU** | no hay corpus de passthrough evaluado aquí. `NOT_DETERMINED` |
| `GAP-07` | **persistencia / worn storage** de la GPU | fuera del alcance de ideas de rendimiento. `NOT_APPLICABLE` |
| `GAP-08` | **cooling físico / resistencia térmica del board** | no observable por software. `NOT_AVAILABLE` |
| `GAP-09` | **carga >13,6 W** (para que el cap ligue) | el corpus nunca ha pasado de 13,6 W; las 5 familias de cap dependen de alcanzar esa carga. `CONTRADICTION_WITH_MEASURED_ENVELOPE` |

---

## 13. `IDEAS_QUE_REQUIEREN_NUEVA_HIPÓTESIS` (11 de 15)

`D2-01` `D2-02` `D2-03` `D2-04` `D2-05` `D2-06` `D2-08` `D2-09` `D2-13` `D2-14` `D2-16`
**No se han escrito.** Destino de una hipótesis: `HYPOTHESIS-REGISTER.md`.

## 14. `IDEAS_QUE_REQUIEREN_NUEVO_EXPERIMENTO` (13 de 15)
Todas salvo `D2-10` (post-proceso) y `D2-15` (bloqueada).
**No se han diseñado.** Destino: `EXPERIMENT-CANDIDATES.md`, con checklist de 8 preguntas.

## 15. `LIMITACIONES`

| # | Limitación |
|---|---|
| `L-01` | `gpuopen.com` devolvió **404** en 2 URLs: sin verificación primaria de arquitectura GFX8 |
| `L-02` | Wikipedia Morphological analysis es *stub*: el método se usó genéricamente, `PUBLICATION_DETAIL=NOT_AVAILABLE` |
| `L-03` | El bloque SIMD citado es de **GCN general**; no verificado que RX550/Polaris12 tenga idéntico conteo de TFU/LDS. `EXTERNAL_KNOWLEDGE`, no evidencia local |
| `L-04` | No se consultó literatura académica (papers): sólo enciclopédica. `LIMITATION` de alcance |
| `L-05` | 52 candidatas demotadas se consolidan en 23 filas de familia (§7–§9); §6.2 conserva las 10 filas sueltas. Trazabilidad por familia, no por candidata individual |
| `L-06` | La búsqueda de huecos fue por **término**: una idea podría cubrir un hueco con otra palabra. Riesgo de falso negativo. `NOT_DETERMINED` |
| `L-07` | `D2-08` (dominios de energía) no tiene evidencia de que el mecanismo exista en GFX8: puede ser idea vacía |
| `L-08` | No se modificó `IDEA-REGISTER.md` ni ningún artefacto del sistema |

## 16. `CONTROL DE COMPLETITUD` (FASE 9, 2 pasadas inversas)

**Pasada A — cada hueco de FASE 1, ¿generó idea?**

| Hueco | ¿Idea? |
|---|---|
| textura/filtro (`C`) | `D2-03` |
| LDS/bancos (`C`) | `D2-04` |
| TLB/page size (`C`) | `D2-05` |
| multi-proceso (`H`, `P`) | `D2-06` (bloqueada por `CON-01`) |
| segundo GPU (`L`) | `D2-01` |
| ruido/repetibilidad (`C`) | `D2-02` |
| effective frequency (`N`) | `D2-09` |
| power domain (`C`) | `D2-08` (sin verificar) |
| firmware/fuses (`B`) | **`GAP-01` sin idea** |
| scanout/underrun (`C`) | **`GAP-02` sin idea** |
| doorbell (`C`) | `VARIANT_OF(R-NEW-25)` — no nueva |
| preemption (`C`) | `SUBIDEA(D2-06)` |
| SMC/uniform datapath (`C`) | `GAP_NO_IDEADO` (dentro de `D2-03` por prox) |
| arbitraje (`E`) | `D2-06` |
| sensor↔estimator (`E`,`N`) | `D2-13` |
| replay/retirement (`C`,`Q`) | `D2-14` (bloqueada) |

**Pasada B — cada idea existente, ¿algún mecanismo externo la transforma?**
`H1`→`D2-12` (moldear en vez de forzar) · `H7`→`D2-12` · `H8`→`D2-06` · `H12`→`VARIANT` (sin idea nueva) · `H4/H5`→`GAP_NO_IDEADO` · `H9`→`VARIANT` · `H10`→`VARIANT` · `H11`→`VARIANT` · `H2`→`D2-12` (vía sin heating) · `H3`→`D2-09` · `H6`→`D2-05` · `R-01`→`D2-13` · `O-ROOT`→`D2-15` · `Q1..Q7`→`D2-14` · `R-NEW-99`→`D2-11`

**Pasada C — cada contradicción, ¿generó idea?**
`CON-01` **NO** · `CON-02` **NO** · `CON-03` **NO** (ya registrada)
`C1 NOT_EXECUTED`→`D2-10` (mining) · `H1 M1 no discriminó`→`D2-11` (calibración) · `R-08 Mesa≈STOCK`→`D2-01` (¿era el otro GPU?) · `P-02/P-03 CONGELADO`→`D2-12`

```
RESULTADO_CONTROL = 11 huecos con idea · 3 contradicciones sin idea · 1 gap sin idea
                    67 candidatas: 15 GENUINELY_NEW + 26 DUPLICATE + 22 VARIANT + 4 SUBIDEA
                    ninguna idea nueva sin mecanismo declarado
                    ninguna idea convertida en hipótesis, experimento o evidencia
```

---

## `ORIGINAL → DESTINO`

```
ideas.txt (184)  ──sin cambios──►  IDEA-REGISTER.md 34e4268a  (NO modificado)

literatura externa (GCN, TRIZ) ──GENERADOR──►  este documento ──preguntas──►  (ninguna)
                                                            │
                            corpus 01-AUDITORIA/FASE-C1/… ─┤
                            14 mecanismos + 40 TRIZ + 7 dimensiones morfológicas ─┘
                                                            ▼
                                              16 GENUINELY_NEW  +  45 demotadas
                                                            ▼
                                          (NO entran a IDEA-REGISTER.md;
                                           NO son hipótesis; NO son experimentos)
```

## Diagrama — familias nuevas y su relación con el corpus

```
                       ┌─ D2-01 segundo GPU ────────┐
                       │  (confound de TODO)        │
   CONTAMINANTES ──────┼─ D2-06 multi-proceso ───────┼──▶ CON-01 (contradice OWNERSHIP)
                       │  (arbitraje)               │      CON-02 (FULL inalcanzable)
                       └─ D2-16 línea base ─────────┘

   INSTRUMENTO ────────┬─ D2-02 piso de ruido ──────┐
                       ├─ D2-11 control negativo ───┤──▶ precondición para TODO lo demás
                       ├─ D2-13 validez sensor ─────┤
                       └─ D2-09 freq. efectiva ─────┘

   RECURSOS NO USADOS ─┬─ D2-03 textura/filtro ────┐
                       ├─ D2-04 LDS/bancos ─────────┤──▶ familias nuevas
                       ├─ D2-05 TLB/page size ───────┤
                       └─ D2-08 dominios energía ────┘   (D2-08 sin verificar)

   MÉTODO ─────────────┬─ D2-10 minar artefactos ────┐
                       └─ D2-12 moldear workload ───┴──▶ desbloquea P-02/P-03/H7 sin escribir

   YA CUBIERTO (45) ──── doorbell→VARIANT(R-NEW-25) · preempt→SUBIDEA(D2-06)
                          TEXTURAS→DUPLICATE(R-NEW-83) · métricas→NO ES IDEA
```

## Diagrama — qué se puede hacer sin autorización

```
SIN ESCRITURA / SIN WORKLOAD      D2-10 mining        ← datos ya preservados
                                 D2-02 piso de ruido  ← corridas repetidas
                                 D2-09 freq. efectiva ← post-proceso
                                 D2-15 migración corpus ← BLOQUEADA por decisión

CON AUTHORIZATION DE WORKLOAD      D2-11 D2-12 D2-16 D2-03 D2-05

CON AUTHORIZATION DE ESCRITURA    D2-08  (observar, quizá sí; intervenir, no)
                                 P-02 P-03  ← siguen CONGELADOS

BLOQUEADAS POR CAPACIDAD          D2-04 D2-14  ← selectores GFX8 prohibidos
BLOQUEADAS POR REQUISITO          D2-06        ← CON-01
```
