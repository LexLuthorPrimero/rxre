# POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md

> **Fase ejecutada:** reparación de referencias post-reorganización — Sets A–G (documentación).
> **Fecha:** 2026-09-23 · **Modo:** parches textuales exactos 1:1, uno por entrada del plan (archivo→referencia→propuesta). Sin sustituciones globales.

## 1. Resumen ejecutivo

- **36 archivos modificados · 120 referencias reparadas** (88 patrones exactos). Verificación de hashes antes/después: **36/36 OK (0 discrepancias)**.
- Existencia de destinos nuevos: **100 %** (incluye wildcard `F2-*` → `F2-control-e1-frag`, `F2-fetch8-ilp`). Sin reemplazos globales; `git diff` = 1:1 (115 insertions / 115 deletions).
- Sets aplicados: **A** (6 archivos), **C** (8), **D** (2), **E** (12), **F** (6), **G** (2).
- **NO aplicado:** Set B (depende de U2), `00-INDICE/README.md` (U1), BENCHMARK-INVENTORY L195/L197 (U4), `MASTER-PLAN:781` (U5), y **todo el Set H** (scripts).
- **Set H confirmado intacto** (10/10 scripts, hashes idénticos). Ningún archivo fuera de los 36 autorizados fue modificado.
- Sin ejecución de benchmarks/scripts/harness/experimentos; sin cambios de sistema; sin symlinks NotebookLM.

## 2. Archivos modificados y cantidad de referencias reparadas

| Conjunto | Archivo | Patrones | Ocurrencias |
|---|---|---|---|
| A | `00-INDICE/FINAL-RESEARCH-STATUS.md` | 1 | 1 |
| A | `00-INDICE/MASTER-PLAN.md` | 8 | 9 |
| A | `00-INDICE/MASTER-RESEARCH-STATUS.md` | 21 | 44 |
| A | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | 3 | 3 |
| A | `00-INDICE/decisions.md` | 1 | 1 |
| A | `00-INDICE/experiments_proposed.md` | 1 | 1 |
| C | `01-AUDITORIA/AUDIT-001/AUDIT-001.md` | 1 | 1 |
| C | `01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/FASE-R1-FINAL-REPORT.md` | 1 | 2 |
| C | `01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/R1-1-GFX8-EVENT-RECONCILIATION.md` | 1 | 1 |
| C | `01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION/FASE-R2-FINAL-REPORT.md` | 1 | 1 |
| C | `01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION/R2-HISTORICAL-EXPERIMENT-INVENTORY.md` | 8 | 8 |
| C | `01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/FUSION-03-INVERTED-MEMORY-HIERARCHY.md` | 1 | 1 |
| C | `01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/README.md` | 1 | 1 |
| C | `01-AUDITORIA/FASE-R3-NOVELTY-AUDIT/FASE-R3-FINAL-REPORT.md` | 1 | 1 |
| D | `02-ARQUITECTURA/evidence.md` | 4 | 5 |
| D | `02-ARQUITECTURA/research_log.md` | 1 | 2 |
| E | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-PLAN.md` | 4 | 6 |
| E | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-PRECHECK.md` | 1 | 2 |
| E | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md` | 2 | 2 |
| E | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL-v2.2.md` | 1 | 1 |
| E | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL.md` | 1 | 1 |
| E | `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md` | 7 | 7 |
| E | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/EXP-F1-A-RESULTADOS.md` | 1 | 2 |
| E | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md` | 3 | 3 |
| E | `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md` | 1 | 1 |
| E | `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/R-14-SUPERPOSITION-DISSECTION.md` | 1 | 1 |
| E | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md` | 2 | 2 |
| E | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/runs/exploratorio-01/RESULTADO-EXPLORATORIO-01.md` | 1 | 1 |
| F | `04-IMPLEMENTACION/FASE-E-REAL-GAME-BASELINE-DESIGN.md` | 1 | 1 |
| F | `04-IMPLEMENTACION/FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md` | 1 | 1 |
| F | `04-IMPLEMENTACION/SYNTHETIC-WORKLOAD-DESIGN.md` | 1 | 1 |
| F | `04-IMPLEMENTACION/rx550-torneo/README-FASE1.md` | 1 | 1 |
| F | `04-IMPLEMENTACION/rx550-torneo/README-FASE2.md` | 1 | 1 |
| F | `04-IMPLEMENTACION/rx550-torneo/README-FASE3.md` | 1 | 1 |
| G | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/FASE-R0-EXTERNAL-KNOWLEDGE-FINAL-REPORT.md` | 1 | 1 |
| G | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-2-POWERPLAY-MCLK-SMU7.md` | 1 | 2 |

| Conjunto | Archivos | Ocurrencias reparadas |
|---|---|---|
| **A** | **6** | **59** |
| **C** | **8** | **16** |
| **D** | **2** | **7** |
| **E** | **12** | **29** |
| **F** | **6** | **6** |
| **G** | **2** | **3** |
| **Total** | **36** | **120** |

## 3. Hashes antes → después por archivo

Tabla completa en `00-INDICE/REGISTRO-DE-REPARACION-REFERENCIAS.md` (§1). Resumen:

| Conjunto | Archivo | SHA256 antes | SHA256 después |
|---|---|---|---|
| A | `00-INDICE/FINAL-RESEARCH-STATUS.md` | `dfdc45714f40aa4569bbf96dc0214a52cb1df28195f580c2461700f8b010a05e` | `5fff6459b2b0062dda852071f83a1f85e5f77dbb2656191479203ae9d8cb58c8` |
| A | `00-INDICE/MASTER-PLAN.md` | `750a162a108c45fd666cbd5e07eb9f4ead8eb4e70dba68a75197244ccd5d4623` | `80dff92acc5469c703b93c63b8f900887e41abed599f9ed5be3f07800cc162e5` |
| A | `00-INDICE/MASTER-RESEARCH-STATUS.md` | `e65893f3e7efe7ca74335538da45106eaa20a6d3286b1aea68a4854ffea5071c` | `e4350f8093d95c4e4705ca68c4eccef9e9e26d2568e6a250a125577280375dea` |
| A | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | `438493db199d6fdb51923cc9b16ea0a3fb01635f2f5eb47a7b7bbc076d8fce95` | `58124ad0d4d0f21a416a2504de7f4de86ed818c14e5a4bccdc0bf9f459781ce4` |
| A | `00-INDICE/decisions.md` | `16fdc2b94e065ce0a64e1d1077b793ab3534de0d7724b4554ac01cbba97052ba` | `8f4a510f18d9c13cf50bc85068b5d8ae4d6c6c6445543444d836cfbe524d6145` |
| A | `00-INDICE/experiments_proposed.md` | `576f8cb8e8f5de0f4a72e50b1fc4efb2d663f9a328291b2348fddbcbef4dc216` | `402b388c8b96ffdc5f640e2b940058c5c74141d1d8f17b917b43b092424cccff` |
| C | `01-AUDITORIA/AUDIT-001/AUDIT-001.md` | `a4059ecb9513d918701ae2e067a2aaa7988f240d8750c339bd8fb34829513326` | `7499e1954ce1b66a1d0d59b4ffcb9ec2e69f98209e76fab6a809fd189d7192fe` |
| C | `01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/FASE-R1-FINAL-REPORT.md` | `0c2a833d52d0aa73f684b73a4b71d813e49feaf892a470e5805a6beed197aa6f` | `4c0d6b90a1ba7e491f6ffd5b16041b88731085e9067425087c2f855f29130dcb` |
| C | `01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/R1-1-GFX8-EVENT-RECONCILIATION.md` | `bc888d0f496614717cd3b6dc42ec3987692d3b4d5560633e8e65d3ea82c09d20` | `c2c316f13af51d82cf366f035b850bf3c5fbbf1251b25962bc731fa0f8703392` |
| C | `01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION/FASE-R2-FINAL-REPORT.md` | `da46de040b3c43a7a7857b6e0587bab98a0d1eb723b3b74da57299af890eca92` | `f4b785abd1472052cd34380018deabe297c8cf6524e6c5df6a65c1a1ee7fa987` |
| C | `01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION/R2-HISTORICAL-EXPERIMENT-INVENTORY.md` | `b36f7d7d615504af8011c03ebb698edb8a3b40dbf94d3e885cf537bf9cd87d2c` | `bd747106c9fd2ef1c7b386339aee7440a5a3b242b3e4a9e022b0d2ce1803c2db` |
| C | `01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/FUSION-03-INVERTED-MEMORY-HIERARCHY.md` | `579f32781682e58875d5116b4510aa275d56e0797e4ed65b7d5e24ec620fb149` | `2984fa28aaf9970cf96bd36828fbb2b8e416f1ab8a1d58f5a368177797e74e43` |
| C | `01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/README.md` | `3b272324600b7e34be322f86496d8dac8bf66812aa325d81b757f3281207150a` | `60cfe155ead5c25f29a9d96160c7eeb668eb4af9276be4701c42084782ad20d2` |
| C | `01-AUDITORIA/FASE-R3-NOVELTY-AUDIT/FASE-R3-FINAL-REPORT.md` | `330c107ed58bb867438481cbfad18dc749fd0732cb0313b4db56127da2319a5d` | `4cefb339788f761fde0212cdf9a0214c1efb693320aebc22fd13921f5841bb74` |
| D | `02-ARQUITECTURA/evidence.md` | `44e7d3002695a4e973ed04a7c20883018b31cd0efe402f97969f44938eacbc95` | `84fa3a78e2ac74e1f2a035b1ec5c4991b20182ac31a29104a413d53b1c5f73df` |
| D | `02-ARQUITECTURA/research_log.md` | `f572fbab376271af057f80cae84277e0125a52daf98ec1ff4138e04c6f084bd9` | `c53a5e1abddd30fe325b8d163048cac81a524f6e28bcd40129a540e4aa6abdf8` |
| E | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-PLAN.md` | `0e8864bbd94b1e29276485d67e9c23cb0da4aa4f157c662fb0f6ca0f5b451d9a` | `0ae15f7d0927353af09e2a0299c8aacc786b40de1394133f09229f1a37a3ea6c` |
| E | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-PRECHECK.md` | `e9aea2f151f56916be8ede77c8dc21132dfd80677cd4ffadeaff5279413de426` | `73daa5663a1de3a490a3704840895171ecd99fced023163cd7dae9f08c25f116` |
| E | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md` | `e1981649fce8f1c6d44f5c981f1467792d95bc0b8ab50003dd48f83c78728009` | `c3523120bbaddc2a724d0af3816bbfe695b589e32cd2c07a37e13bfa5787698c` |
| E | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL-v2.2.md` | `d51b29d602c6a5d50c846205e8a8b112c07e661ab00141b7ddfb0e3e88aeae10` | `b31a08c23dc249617421ddb9fd72e4fe21a6fd0e05a569a8635f3cfc6aa64449` |
| E | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL.md` | `b9040cc703648cb3d30bb4d3a6230161c63ebac3aefe58bbc27459cbb4d1bccf` | `07504843b211c7bd603cfff8585af6e55900acc57ce814f5c3dc35e791e3d051` |
| E | `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md` | `18813caa1749e00e9d645d2a5010c8233123dba62e5da1631a925c215b3ee908` | `5a88bca815c93f81a3d2e2d2fdecba843447de66b4ffc350747b58fd4d60990b` |
| E | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/EXP-F1-A-RESULTADOS.md` | `3374fd17fab3611f94e23e17624bf196b55ee8bafd07f700c51d6e7f31a0fa46` | `cf985b7e23da0dced1c771c992943db015b44a6a862be6af23b6620131ddcb05` |
| E | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md` | `79e22d8a733d3fa64aceb088e8914806b4015a757425c9eeff2e369cb63b8d16` | `bcdec8d521b405c6a83b06d60480a692912e566d4524ebe3ae8f41dbe0cff6c2` |
| E | `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md` | `469d206baff2ad5443ac32600e023dbf425123c202625204f83ddb6d6778751c` | `d6390e7a611c9392d015604f791a3de63b7fef456ecba721d61463984d23b558` |
| E | `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/R-14-SUPERPOSITION-DISSECTION.md` | `a584e981023a19fe29d0790b6b5fae88402c1fc091b050a72f220b108d9e925b` | `b6e7cf260c4635360604de15f88036a8d7b2f15d69cec35ed180971b3cdaa24c` |
| E | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md` | `db50b813c4f584529003aa6f39ae6d4264519bea9afa78c4c5836e037b58c1a2` | `4f439c52152bf7515095f0a89cbd2cb127d15758437fb30fb8887406ae52ee23` |
| E | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/runs/exploratorio-01/RESULTADO-EXPLORATORIO-01.md` | `57364aea94fb6741ca3383dc7695919e8500a124b04775bcb7913ae14bd1bd66` | `2bf4f1057b453da65dbfe9ea0516618d944a07cba545b124f2a35f536925f898` |
| F | `04-IMPLEMENTACION/FASE-E-REAL-GAME-BASELINE-DESIGN.md` | `40de3e2c841e3055d1cb65795b0113cf8660771d83ec00dbb51ec4b0fe8fa785` | `089290bdbd28cb7ee2fcaf98e15e0bed8a2cb964a9eddf0bf773bcedd0103ab8` |
| F | `04-IMPLEMENTACION/FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md` | `0640f5f51b18c897f59b59accbdb415e38f4cc405f9c92deee5fcbe79449e939` | `9b0c0263b566d0b4a9da3d396dd70b138e1c5f8c8cbfac6300e7adab7f090b18` |
| F | `04-IMPLEMENTACION/SYNTHETIC-WORKLOAD-DESIGN.md` | `1299295459621cbefe0e6625da45430b71b7d6857bd38672c91180ae0ad85720` | `04c2115476eb042f953cc1ac972544881c5ea1915c3c3fb2b6ca170fea8b020f` |
| F | `04-IMPLEMENTACION/rx550-torneo/README-FASE1.md` | `4f4f6e816d5e66d913d36adad7788ca2a6c3b4353bf7ef5d5da439e5a879eb16` | `319e6f9937ab8b965e3eadeacf869be949a949d7104b9ce3225402f94f6a1380` |
| F | `04-IMPLEMENTACION/rx550-torneo/README-FASE2.md` | `50b40f20c555aef6f372d810736348c1cc1f358f20699e52aca440e3dd73f626` | `a87b364d4ab2bc65c6a2c04d9c8796cf68180ec3579a021287b3172a79af85e0` |
| F | `04-IMPLEMENTACION/rx550-torneo/README-FASE3.md` | `a94463b868c2d7f56c09e0d0ce4a40121d6aa34b8531b3f0525bf426d73bc38d` | `18d8124c560e0b13ce8ac62d4c193326681d5ec07b2717ec6755ecd09aae94f7` |
| G | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/FASE-R0-EXTERNAL-KNOWLEDGE-FINAL-REPORT.md` | `66d3838c5cedfda4bb63709e54b87cc4f2c18ad9580a143901ec698dc57272f6` | `6487a61dfbea23b175a5085f356e26ecd7d22d41fa8fe947418c1a286b8e68d2` |
| G | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-2-POWERPLAY-MCLK-SMU7.md` | `a1787755db69434f2089ca6041a85b91574dc7247a5d9cee3bd0c35b954e3817` | `e09e73b629c5374695a672b29ff50c9cf3dbf470882f6445968537c648e5f86c` |

## 4. Referencias que quedaron pendientes (no reparadas)

### 4.1 Excluidas por UNKNOWN (autorización explícita)
- **U1** — `00-INDICE/README.md` completo (Set A): rol del README (índice activo vs deprecar) sin decidir → excluido.
- **U2** — Set B completo: `R2-GLOBAL-DOCUMENTATION-MAP.md` (alcance: mapa vivo completo vs snapshot + mapa nuevo) → excluido.
- **U4** — `BENCHMARK-INVENTORY.md` L195/L197 (candidatas Set G) → excluido.
- **U5** — `MASTER-PLAN:781` (prosa descriptiva del mapa documental: `(raíz, experiments/ A–D/R-0/R-1/sintético, …)`) → excluido.
- **U3 / Set H** — re-ejecución futura de harnesses: Set H completa queda para su propia fase de autorización (validación ejecución/CWD/PYTHONPATH).

### 4.2 Nuevos hallazgos detectados en la auditoría posterior (vivas → `04-IMPLEMENTACION/projects/`, NO planificadas)
- `MASTER-PLAN.md` L793–L796 (`projects/BERRETA`, `GHOST`, `RX-COMPRESSION-ENGINE`, `ORCHESTRATOR` → diseños).
- `PROJECT-DOCUMENTATION-STATUS.md` L47 y L51–L54 (sección *Proyectos propios* + filas BERRETA/Ghost/RX-Compression/Orquestador).
- `FASE-R3-NOVELTY-AUDIT/FASE-R3-FINAL-REPORT.md` L119 (`projects/I-*`).
- `TEST-TERMICO-READONLY.md` L43 y L45 (`projects/CLOSED-LOOP-QUALITY-GOVERNOR/*`).
- `FASE-R4C-JITTER-OBSERVABILITY/PRECHECK-REPORT.md` L12–L14 (`projects/JITTER-REPROJECTION`, `projects/BERRETA`).
- `MASTER-PLAN.md` L82 (`~/Escritorio/berchmark/…`, exterior deliberado) → **no reparable**, se mantiene.

> Estas referencias **no estaban en el plan aprobado**; quedan registradas para un set futuro (Set I candidato) y **no fueron tocadas**.

### 4.3 Media confianza / históricas mantenidas
- `FASE-R2-FINAL-REPORT.md` L64 y L185 (descripción del árbol en el mapa y conteo de documentos de la fase R-2): descripción del snapshot histórico → no modificadas.
- Históricas deliberadamente intactas (backup/método): `R2-HISTORICAL-EXPERIMENT-INVENTORY.md` L19/L20/L30/L54/L193–L199; `02-ARQUITECTURA/evidence.md` L25; `FASE-R2-FINAL-REPORT.md` L42/L46/L65/L88/L92–L95/L162–L165/L187.

## 5. UNKNOWN restantes

| ID | Tema | Estado |
|---|---|---|
| U1 | Rol de `00-INDICE/README.md` (índice activo vs deprecar) | Pendiente decisión |
| U2 | Alcance exacto de `R2-GLOBAL-DOCUMENTATION-MAP.md` (Set B) | Pendiente decisión |
| U3 | Re-ejecución futura de harnesses (impacta prioridad Set H) | Pendiente decisión |
| U4 | `BENCHMARK-INVENTORY.md` L195/L197 (extensión Set G) | Pendiente decisión |
| U5 | `MASTER-PLAN:781` (cosmética descriptiva) | Pendiente decisión |

## 6. Confirmación: Set H NO modificado

| Script | SHA256 (antes = después) |
|---|---|
| `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/telemetria.sh` | `20102c31eae590e66d5e204270780723a833c07d72a72bcec777a6b8200e9de2` |
| `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/etapa2/analizar_etapa2.py` | `b76c531e8a9b129b4a76514e779161e98352f46b76416c54fb7e33d6fff770e2` |
| `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/etapa2/auditoria_reconstruccion.py` | `5574b6769c76aa02ccf1d3e505f2b97819b0c2a5b11531ec7a3e2a57fefd9e79` |
| `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/etapa2/orquestador.sh` | `8026df2212e79c08aa42cc7565ac5404dbf069826903c0ba412f587016a743e3` |
| `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/telemetry/telemetria.sh` | `922c429b9a78e0064f188fbc147da1af5fbca1429a888cec1174f7ec962db2e6` |
| `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/run_thermal_replicate.sh` | `8933187601426f1deba38fb2706efdef291891f6427387fe837fdb4671c1d957` |
| `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/harness/run_all.sh` | `d0e94ef55cc60ae6f9e6aa61e1c55c86115df5ce1334bc12ff4f64b9e3ce9aed` |
| `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/run_superposition.sh` | `0ed5f34ff67fcdcfaf472e91ab7045f8ed8c2e5f328c190c3db5dea32d676efb` |
| `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/soak-final.sh` | `8d666328d6e956b190e709b74a980f7ded3fdaa119ff1a4459d20ff1506a5e2b` |
| `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/soak-probe.sh` | `4d6a12b8bb2f38d7839856e6f61ee8546bba7e91de7067d9f2e518df3e40960c` |

## 7. Auditoría posterior de referencias (condición 9)

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Las referencias vivas reparadas apuntan a destinos existentes | ✅ | Verificación dirigida de las 120 referencias nuevas: 100 % existen (token `F2-*` resuelto por glob) |
| No quedaron rutas antiguas reparables de los Sets A–G | ✅ | Barrido residual: solo restan refs históricas intencionales, U5 y pendientes §4 (ninguna reparable de A–G) |
| Referencias históricas permanecen intactas | ✅ | `git diff` por archivo: cambios limitados a líneas del plan (§3); backups/métodos sin alteración |
| No se modificaron archivos fuera de los autorizados | ✅ | `git status` + `git diff --stat`: exactamente los 36 archivos; logs/CSV/TSV/sysfs/snapshots/manifests/NotebookLM/Mesa/PROYECTOS_LUCAS/exports sin cambios |
| Scripts del Set H no modificados | ✅ | Hashes 10/10 idénticos (§6) |

## 8. Entregables y estado de Git

- Creados en esta fase: `00-INDICE/REGISTRO-DE-REPARACION-REFERENCIAS.md` y `00-INDICE/POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md`.
- Los 36 archivos parcheados + los 4 informes permanecen **sin commit** (pendiente de instrucción explícita; mismo criterio que los 2 informes de FASE 7).
- **Bloqueado hasta autorización separada:** Set H (scripts); `FUENTES-FALTANTES.md`; `IMPLEMENTATION-ROADMAP.md`; `IMPLEMENTATION-SAFETY-RULES.md`; symlinks NotebookLM.
- Regla de detención respetada: ninguna corrección falló la verificación → no hubo paradas intermedias por error.

## 9. Registro de verificación (resumen técnico)

- `sha256sum` antes: `00-INDICE`-previo a parche, 36 archivos (idéntico al baseline Git).
- `sha256sum` después: recalculado post-parche; cruzado fila a fila con `REGISTRO-DE-REPARACION-REFERENCIAS.md` → 0 discrepancias.
- `git diff --stat`: 36 archivos, +115/−115 líneas (solo 1:1).
- `git status --porcelain`: únicamente los 36 `M` + 4 untracked (informes).
