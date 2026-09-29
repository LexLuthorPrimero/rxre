# ROUTING-SCHEMA — Vocabulario del router

**Fecha:** 2026-09-25T23:10Z
**Propietario del vocabulario base:** `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` (taxonomía R2),
ampliado de forma mínima y documentada. **No se crea una taxonomía paralela.**

---

## 1. `DOMAIN` — 12 dominios

Derivados de la agrupación de los 68 topics del censo. No son inventados: cada dominio agrupa
topics que comparten `PRIMARY`.

| # | `DOMAIN` | Topics que contiene | `PRIMARY` típico |
|---:|---|---|---|
| D1 | `PROJECT_STATE` | PROJECT_STATUS, PROBLEM_MATRIX, RELEASE, GITHUB, DECISIONS, ROADMAP, DOCUMENTATION_MAP, DIAGRAMS | `README.md` → `PROBLEM-STATUS-FINAL.md` |
| D2 | `PATCH_AND_CORRECTION` | PATCHES, ROLLBACK, INSTALLATION | `PATCH-REGISTRY-FINAL.md` |
| D3 | `HOST_IDENTITY` | HOST_IDENTITY, KERNEL, FIRMWARE, BACKUP | `PATCH-SOURCES.md` §3 (única fuente HOST-C) |
| D4 | `GPU_ARCHITECTURE` | RX550, GPU, POLARIS12, GFX8, AMDGPU, DRM, PCI, VRAM, SMU | `02-ARQUITECTURA/knowledge.md` |
| D5 | `POWER_AND_CLOCKS` | POWER_CAP, DPM, SCLK, MCLK, RUNTIME_PM, GOVERNOR | `RESULTADOS-M1.md` |
| D6 | `GRAPHICS_STACK` | MESA, RADV, VULKAN, OPENGL, WAYLAND, KWIN, XWAYLAND, INTEL_GPU, WSI | `PATCH-REGISTRY-FINAL.md` |
| D7 | `MEASUREMENT` | COUNTERS, TELEMETRY, FRAME, BENCHMARKS, SUPERPOSITION, GLMARK2, M1, R4B, R4C, EXPERIMENTS, REPRODUCIBILITY | por experimento |
| D8 | `ISOLATION_AND_C1` | C1, OWNERSHIP, RECOVERY, TTY, D_STATE, GATES | `C1-ISOLATION-DESIGN-v1.0.md` |
| D9 | `STORAGE` | STORAGE, HDD, BTRFS, SMART, IO, PSI | `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` |
| D10 | `BACKGROUND_AND_SERVICES` | SYSTEMD, KALM, AUTOPILOT, BACKGROUND, IRQ | `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` |
| D11 | `PASSTHROUGH` | VFIO, IOMMU, IOMMU, BACO | `VFIO-FEASIBILITY-AUDIT-20260925T132242Z.md` |
| D12 | `GOVERNANCE` | SECURITY, SAFETY, VOCABULARY, TEST, OPENCODE, AGENT_RULES | `AGENTS.md` |

**Asignación de topics a dominios (68 topics, cobertura completa):**

| Domain | Topics |
|---|---|
| D1 | PROJECT_STATUS, PROBLEM_MATRIX, RELEASE, GITHUB, DECISIONS, ROADMAP, DOCUMENTATION_MAP, DIAGRAMS, HISTORY, CHANGELOG |
| D2 | PATCHES, ROLLBACK, INSTALLATION, PROJECT_OVERVIEW |
| D3 | HOST_IDENTITY, KERNEL, FIRMWARE, BACKUP, RESET |
| D4 | RX550, GPU, POLARIS12, GFX8, AMDGPU, DRM, PCI, VRAM, SMU |
| D5 | POWER_CAP, DPM, SCLK, MCLK, RUNTIME_PM, GOVERNOR, MCLK |
| D6 | MESA, RADV, VULKAN, OPENGL, WAYLAND, KWIN, XWAYLAND, INTEL_GPU, WSI |
| D7 | COUNTERS, TELEMETRY, FRAME, BENCHMARKS, SUPERPOSITION, GLMARK2, M1, R4B, R4C, EXPERIMENTS, REPRODUCIBILITY |
| D8 | C1, OWNERSHIP, RECOVERY, TTY, D_STATE, GATES |
| D9 | STORAGE, HDD, BTRFS, SMART, IO, PSI |
| D10 | SYSTEMD, KALM, AUTOPILOT, BACKGROUND, IRQ |
| D11 | VFIO, IOMMU, BACO |
| D12 | SECURITY, VOCABULARY, TEST, OPENCODE, AGENT_RULES, SAFETY, FIREFOX, GRUB, UDEV, HYPOTHESIS, DESIGN |

Nota: los 4 topics sin primaria (`BACO`, `FIREFOX`, `GRUB`, `UDEV`) están asignados a dominios
para que el router sepa dónde buscarlos y sepa que no los encuentra. `BACO`→D11,
`FIREFOX`/`GRUB`/`UDEV`→D12.

---

## 2. `QUESTION_TYPE` — 21 tipos

Los 18 del encargo más 3 descubiertos en el censo.

| # | `QUESTION_TYPE` | Pregunta típica | `TERMINAL` esperado |
|---:|---|---|---|
| Q1 | `STATUS` | ¿En qué estado está X? | Estado del `PROBLEM_MATRIX` |
| Q2 | `HARDWARE` | ¿Qué hardware es / tiene? | `HOST_IDENTITY` + `POLARIS12` |
| Q3 | `CONFIGURATION` | ¿Cómo está configurado X? | `INSTALL.md` / `PATCH-REGISTRY-FINAL.md` |
| Q4 | `EXPERIMENT` | ¿Qué experimento existe para X? | Nombre y `.md` del experimento |
| Q5 | `RESULT` | ¿Qué dio el experimento X? | `RESULTADOS-*.md` |
| Q6 | `CAUSALITY` | ¿Por qué pasó X? | Casi siempre `UNKNOWN` o `CONFLICT` |
| Q7 | `REGRESSION` | ¿Algo se rompió? | `PROBLEM-STATUS-FINAL.md` |
| Q8 | `PATCH` | ¿Qué parche hay para X? | `PATCH-REGISTRY-FINAL.md` / `PATCH-REGISTRY-RECOVERED.md` |
| Q9 | `IMPLEMENTATION` | ¿Existe implementación de X? | `C1-ISOLATION-AUTOMATOR.md` / `H12-1/README.md` |
| Q10 | `RECOVERY` | ¿Cómo se recupera? | `ROLLBACK.md` + preflight |
| Q11 | `STORAGE` | ¿Qué pasa con el disco? | Gate P0 §storage |
| Q12 | `GRAPHICS` | ¿Qué pasa con el stack gráfico? | `PATCH-REGISTRY-FINAL.md` |
| Q13 | `POWER` | ¿Qué pasa con la potencia? | `RESULTADOS-M1.md` |
| Q14 | `DOCUMENTATION` | ¿Dónde está documentado X? | El propio router |
| Q15 | `REPRODUCIBILITY` | ¿Se puede reproducir X? | `TESTING.md` + experimento |
| Q16 | `GITHUB` | ¿Se puede publicar? | `RELEASE-CANDIDATE.md` |
| Q17 | `SECURITY` | ¿Qué está prohibido / es secreto? | `AGENTS.md` + `RELEASE-EXCLUSIONS.md` |
| Q18 | `HISTORY` | ¿Qué pasó históricamente? | Inventario R-2 / `AUDIT-001/` |
| **Q19** | **`HOST_IDENTITY`** *(nuevo)* | ¿Qué SO/kernel/Mesa tiene la máquina **ahora**? | `PATCH-SOURCES.md` §3 + re-medición |
| **Q20** | **`TELEMETRY`** *(nuevo)* | ¿Cómo se midió / qué esquema tiene? | `TELEMETRY-SCHEMA.md` / addendum |
| **Q21** | **`VALIDITY`** *(nuevo)* | ¿Ese resultado es válido? | Gate P0 + `DOCUMENTARY-RECONCILIATION` |

`Q19` es nuevo porque el censo discovered que «¿qué tiene la máquina?» es una pregunta
**distinta** de «¿cómo está configurado?»: la primera tiene tres respuestas incompatibles
(HOST-A/B/C) y la segunda tiene una respuesta con `STALE` marcado.

`Q21` es nuevo porque el proyecto tiene un eje de *validez experimental* (Gate P0, perturbación,
contaminación) que no encaja en `RESULT`: un resultado puede existir y no ser válido.

---

## 3. `EVIDENCE_TYPE` — taxonomía R2 + 5 extensiones

### 3.1 Tokens reutilizados de R2 (sin cambios)

R2 §0 define: **REP**, **DISEÑO**, **PLAN**, **ESTADO**, **REF**, **AUDIT**, **CIERRE**.
Sus tablas añaden: **MAPA**, **ÍNDICE**, **ADDENDA**, **CÓDIGO**, **SPEC**, **DIAGRAMA**,
**REGISTRO**.

| Token R2 | Significado en R2 | `CATEGORY` equivalente del censo |
|---|---|---|
| `REP` | reporte de resultados | `EXPERIMENT_RESULT` |
| `DISEÑO` | diseño no ejecutado | `DESIGN` |
| `PLAN` | plan de ejecución | `EXPERIMENT` (protocolos) |
| `ESTADO` | estado del proyecto | `STATUS` |
| `REF` | referencia / datos | `REFERENCE`, `EXTERNAL_SOURCE` |
| `AUDIT` | auditoría | `ANALYSIS` |
| `CIERRE` | documento de conocimiento concluido | `ANALYSIS` (subtipo) |
| `MAPA` | mapa de subsistemas | `INDEX` |
| `ÍNDICE` | índice de directorio | `INDEX` |
| `ADDENDA` | addenda a un estado | `ANALYSIS` |
| `CÓDIGO` | código fuente | `IMPLEMENTATION` |
| `SPEC` | especificación de build | `REFERENCE` |
| `DIAGRAMA` | vista Mermaid derivada | `INDEX` |
| `REGISTRO` | registro de hipotesis/traceability | `HYPOTHESIS` |

### 3.2 Las 5 extensiones mínimas

| Token | Definición | Por qué R2 no basta | Filas del censo |
|---|---|---|---:|
| `RAW` | Artefacto de medición: `.csv`, `.log`, `stdout.txt`, `state_*.txt`, `telemetry.*`, `metrics.json` de corrida | R2 llama `REF` a documentos como `R0-1-GFX8-EVENT-IDS.md` y también a artefactos. El router necesita distinguir un `.md` de 3 KB de un `stdout.txt` de 40 KB porque **solo el primero se lee directamente** | 1321 |
| `PATCH` | Registro de corrección o de recuperación de parche | R2 no tiene tipo para ello; el censo tiene `CATEGORY=PATCH` | 1 + 3 |
| `TEST` | Documento o suite de pruebas | R2 no distingue pruebas de resultados | 2 |
| `RECOVERY` | Preflight, recovery, TTY, C1 | En este proyecto el recovery es un eje de gates completo, no un `REF` cualquiera | 12 |
| `CONFLICT` | Documento cuyo propósito es registrar discrepancias y su precedencia | Sin esto, un `AUDIT` que contiene `CONFLICT` se lee como `AUDIT` fiable | ~6 |

**Total: 19 tokens.** 14 reutilizados de R2 + 5 nuevos. No hay taxonomía paralela.

### 3.3 `CATEGORY` (censo) → `EVIDENCE_TYPE` (router)

| `CATEGORY` censo | filas | → `EVIDENCE_TYPE` |
|---|---:|---|
| `DESIGN` | 65 | `DISEÑO` |
| `ANALYSIS` | 71 | `AUDIT` o `ADDENDA` o `CONFLICT` según el fichero |
| `EXPERIMENT_RESULT` | 28 | `REP` |
| `EXPERIMENT` | 15 | `PLAN` |
| `STATUS` | 13 | `ESTADO` |
| `INDEX` | 21 | `ÍNDICE` o `MAPA` o `DIAGRAMA` |
| `RECOVERY` | 12 | `RECOVERY` |
| `IMPLEMENTATION` | 8 | `CÓDIGO` |
| `EXTERNAL_SOURCE` | 10 | `REF` |
| `HYPOTHESIS` | 3 | `REGISTRO` |
| `DECISION` | 3 | `ESTADO` (subtipo decisión) |
| `REFERENCE` | 3 | `REF` / `SPEC` |
| `TEST` | 2 | `TEST` |
| `PATCH` | 1 | `PATCH` |
| `RAW_EVIDENCE` | 1321 | `RAW` |

---

## 4. `TEMPORALITY` — 7 valores

| Valor | Definición operativa | `SOURCE_STATUS` del censo | Filas |
|---|---|---|---:|
| `CURRENT_NEW_DISK` | Redactado o medido en el disco actual, y el host no ha cambiado desde | `CURRENT_NEW_DISK` | 15 |
| `CURRENT_NEW_DISK_STALE_HOST` | Redactado en el disco actual, pero **el host cambió después** | `CURRENT_NEW_DISK_STALE_HOST` | 2 |
| `HISTORICAL_OLD_DISK` | Host anterior (HOST-A) | `HISTORICAL_OLD_DISK` | 1444 |
| `HISTORICAL_OTHER_HOST` |cita el backup externo, fuera del repo | *(nuevo; vacío)* | 0 |
| `MIXED` | Mezcla contextos sin marcarlo | `MIXED` | 110 |
| `EXTERNAL` | Fuente externa (R0, benchmarks) | `CATEGORY=EXTERNAL_SOURCE` | 10 |
| `UNKNOWN` | No determinable | `SOURCE_STATUS=UNKNOWN` | 4 |

**Regla de resolución (precondición, ver `DOCUMENTATION-ROUTER-DESIGN.md` §6).**

---

## 5. `HOST_SCOPE` — 5 valores

| Valor | SO / kernel / Mesa / `cardN` RX550 | Docs que citan su host en el texto |
|---|---|---:|
| `HOST-A` | Nobara 44 · `7.2.4`/`7.2.6` · Mesa 26.2.2/26.2.3 · `card1` | 18 |
| `HOST-B` | Nobara 43 · `6.18.2-…fc43` · Mesa 25.3.2 · `card2` | 8 |
| `HOST-C` | Nobara 44 · `7.1.3-…fc44` · Mesa 26.2.3 · `card1` | 1 (`PATCH-SOURCES.md`) |
| `UNKNOWN` | El documento no declara host | **229 de 256** |
| `NOT-APPLICABLE` | Documento de diseño/taxonomía/índice | ~12 |

**Atribución por defecto cuando el texto no dice nada:** el censo asigna
`SOURCE_STATUS=HISTORICAL_OLD_DISK` a 126 docs `.md` por su pertenencia a fases, directorios y
fechas. Eso es **atribución por procedencia, no por declaración**. El router debe distinguir:

- `HOST_SCOPE=A-DECLARED` — el documento cita `fc44`/`7.2.x` (18 docs)
- `HOST_SCOPE=A-INFERRED` — atribuido por procedencia del censo, no declarado (126 docs)

**El router expone ambas formas.** Una afirmación de `HOST-A-INFERRED` es más débil que una de
`HOST-A-DECLARED` y debe marcarse como tal.

---

## 6. `SOURCE_PRIORITY` — 4 valores

Reutilizado del censo sin cambios.

| Valor | Definición | Nº (docs) |
|---|---|---:|
| `PRIMARY` | Fuente a consultar primero para el topic | 34 |
| `SECONDARY` | Complementa o explica al primario | 89 |
| `TERTIARY` | Contexto; no debe consultarse primero | 133 |
| `RAW_EVIDENCE` | Artefacto original; nunca se lee en el primer salto | 1320 |

---

## 7. Campos del router: `DOMAIN-INDEX` → `PRIMARY`

El router no replica las 1576 filas. Replica **solo 68 filas de topic**, y cada fila referencia
el censo. Formato de la tabla del router (una fila por topic):

```
TOPIC
DOMAIN
QUESTION_TYPE[]
PRIMARY_SOURCE            (ruta exacta, 1)
TEMPORALITY               (7 valores)
HOST_SCOPE                (5 valores)
SECONDARY_SOURCES[]       (0-3 rutas)
RAW_EVIDENCE              (ruta del EXPERIMENT_MD, no del artefacto)
EXPERIMENT_DIR            (15 buckets)
ESCALATION_CONDITION      (UNKNOWN | CONFLICT | NOT_AVAILABLE | NONE)
CONFIDENCE                (HIGH | MEDIUM)
```

**Decisión: 68 filas, no 1576.** Es una reducción del 96 %. Los artefactos no se listan: se
alcanzan por `EXPERIMENT_DIR` + convención de nombre. La tabla completa de los 68 topics con su
`FIRST/SECOND/RAW/ESCALATION` ya existe en
`01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-TOPICS.md` §15 y el router solo añade
`DOMAIN`, `QUESTION_TYPE[]`, `TEMPORALITY` y `HOST_SCOPE`.

---

## 8. Extensión propuesta del inventario

Tres columnas nuevas para `DOCUMENTATION-INVENTORY.tsv` (fase de implementación):

| Columna | Valores | Origen | Rellenado |
|---|---|---|---|
| `EXPERIMENT_DIR` | 15 buckets de `03-EXPERIMENTOS/` o `""` | Derivado de `PATH` (1297/1321 filas) | Automático |
| `EXPERIMENT_MD` | ruta del `.md` de entrada, o `""` | `.md` en la raíz del `EXPERIMENT_DIR` | Automático |
| `HOST_SCOPE` | `A-DECLARED`, `A-INFERRED`, `B-DECLARED`, `B-INFERRED`, `C-DECLARED`, `UNKNOWN`, `NOT-APPLICABLE` | Escaneo de `fc4[34]`/`7\.2\.[46]`/`6\.18\.2` | Semi-automático + revisión |

Las 20 columnas actuales se conservan. El TSV pasaría de 20 a 23 columnas.

**Verificación de que `EXPERIMENT_MD` es resoluble:** los 15 directorios de `03-EXPERIMENTOS/`
con `.md` tienen cada uno su `.md` en la raíz del directorio (`RESULTADOS-M1.md`,
`EXP-F1-A-RESULTADOS.md`, `ESTADO-HISTORICO-NO-UTILIZABLE.md`, etc.). Correspondencia 1:1
verificada.

---

## 9. `CONFLICT` — registro de los 6

| `CONFLICT_ID` | Asunto | Fuentes enfrentadas | Precedencia declarada |
|---|---|---|---|
| `C1` | Recuento de tests C1 | `C1-TECHNICAL-RECORD.md` (24/24) · `DIAGRAMAS/12` (37/37) · sidecar (44/44) | Sí — `DOCUMENTARY-RECONCILIATION-2026-09-25.md:187-201` |
| `C2` | Versión de Mesa | `DOCUMENTARY-RECONCILIATION` (26.2.2 vs 26.2.3) · raíz (25.3.2) · host vivo (26.2.3) | Parcial |
| `C3` | Versión de kernel | `P0-GATE`/`C1` (7.2.6) · `knowledge.md` (7.2.4) · raíz (6.18.2) · vivo (7.1.3) | «No se funden» |
| `C4` | `cardN` de la RX550 | captura (`card2`) · vivo (`card1`) · scripts (`card1/hwmon2`) | Sí, como regla |
| `C5` | Estado de H12-4 | `H12-1/README.md` (implementado) · reconciliación (no ejecutado) · `PATCH-REGISTRY-FINAL` (NOT_REPRODUCED) | No |
| `C6` | Btrfs | `AGENTS.md` (CONFLICT) · host vivo (ext4) | No |

**Formato de salida del router ante un conflicto:**

```
STATUS=CONFLICT
CONFLICT_ID=C3
SOURCES:
  - 01-AUDITORIA/FASE-P0-.../P0-...-2026-09-24.md   TEMPORALITY=HISTORICAL  HOST_SCOPE=A-DECLARED  VALUE=7.2.6-201.nobara.fc44
  - 02-ARQUITECTURA/knowledge.md                       TEMPORALITY=MIXED       HOST_SCOPE=A-DECLARED  VALUE=7.2.4-201.nobara.fc44
  - README.md                                          TEMPORALITY=CURRENT     HOST_SCOPE=B-DECLARED  VALUE=6.18.2-200.nobara.fc43
  - 01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md       TEMPORALITY=CURRENT     HOST_SCOPE=C-DECLARED  VALUE=7.1.3-200.nobara.fc44
PRECEDENCE_DECLARED=PARTIAL ("no se funden", C1-TECHNICAL-RECORD.md:48)
RESOLUTION=NONE — el router no elige
```

---

## 10. `BROKEN_REFERENCE` — 4 familias

| `REASON` | N | `RESOLVES_TO` conocido | Reparado |
|---|---:|---|---|
| `REORG-2026-09-23` | ~70 | Sí, en 66 de 70 | **No** |
| `OLD-DISK-FILE` | ~30 | N/A — cita un fichero del HOST-A | N/A |
| `RUNTIME-UNVERSIONED` | ~25 | N/A — lo crea el runner | N/A |
| `AMBIGUOUS-PATH` | ~15 | Parcialmente | **No** |

Las 4 familias están catalogadas en `DOCUMENTATION-CENSUS/DOCUMENTATION-RELATIONSHIPS.md` §5 con
la referencia exacta y los documentos que la citan.

---

## 11. `NOT_AVAILABLE` — los 4 topics sin primaria

| `TOPIC` | `PRIMARY_SOURCE` | `TERMINAL` | `WEB_VALID` |
|---|---|---|---|
| `BACO` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | No (no hay especificación upstream relevante) |
| `FIREFOX` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | Sí, pero sería `EXTERNAL`, no estado del proyecto |
| `GRUB` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | Sí (`EXTERNAL`) |
| `UDEV` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | Sí (`EXTERNAL`) |

**El router no escala a `SECONDARY` ni a `RAW` para estos 4.** Devuelve el terminal con la
lista de menciones como contexto, marcada como mención y no como evidencia.

---

## 12. `PATCH_CLASS` — 4 clases

| Clase | Definición | `APPLIED_ON_HOST_C` | Fuente |
|---|---|---|---|
| `STATIC_PROJECT_PATCH` | Código/scripts/tests/validador/documentación del proyecto | `PARTIAL` | `PATCH-REGISTRY-RECOVERED.md` §A |
| `SYSTEM_PATCH` | Unidad systemd, power cap, DPM, udev, sysctl, Mesa | **`NO`** | §B |
| `EVIDENCE` | El registro y su procedència | `N-A` | `PATCH-SOURCES.md` |
| `HYPOTHESIS` | Sin fuente recuperable | `NOT_AVAILABLE` | `RX550-UNK-01`, `KP-01`, `AG-01`, `GR-01` |

**Negativo verificado (HOST-C, 2026-09-25T22:22Z):** 0 unidades `kalm*`, 0
`system-autopilot*`, sin `/opt/kalm`, sin `/usr/local/bin/kalm*`, sin
`/opt/mesa-26.2.2-rx550-haswell`. Ningún `SYSTEM_PATCH` está aplicado.

---

## 13. Validación del esquema

| Comprobación | Resultado |
|---|---|
| Tokens de `EVIDENCE_TYPE` reutilizados de R2 | 14 de 19 |
| Extensiones mínimas | 5, cada una justificada |
| Taxonomías paralelas creadas | **0** |
| Topics con `PRIMARY_SOURCE` resuelto | 64 de 68 |
| Topics con `PRIMARY_SOURCE=NOT_AVAILABLE` | 4 (`BACO`, `FIREFOX`, `GRUB`, `UDEV`) |
| Filas del router | 68 (6 % de las 1576 del censo) |
| `DOMAIN`s con al menos un topic | 12 de 12 |
| `QUESTION_TYPE`s con `TERMINAL` definido | 21 de 21 |
| Valores de `TEMPORALITY` mapeados desde el censo | 7 de 7 |
| `HOST_SCOPE` con baseline medido | Sí: 229/256 `UNKNOWN` |
| Rutas citadas que existen | Verificado en `ROUTING-SIMULATION.md` |
