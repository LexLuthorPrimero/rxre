# DOCUMENTATION-CENSUS — Censo y cartografía documental

**Fecha:** 2026-09-25T22:40Z
**Fase:** FASE 0 — CENSO Y CARTOGRAFÍA DOCUMENTAL
**Alcance:** inventario exhaustivo de la documentación de `~/Escritorio/RX550-INVESTIGACION`
para diseñar después un sistema de navegación por intención.

**Lo que NO se hizo en esta fase** (según lo indicado): no se creó `DOCUMENTATION-ROUTER.md`,
ni `DOCUMENTATION-MAP.md`, ni ningún `*DOC-INDEX.md`; no se reorganizó, movió, renombró ni borró
ningún archivo; no se modificó código, sistema ni Git; no se hizo commit ni push. Solo se han
creado los cinco ficheros de este directorio.

## Documentos de esta fase

| Fichero | Función | Formato |
|---|---|---|
| `DOCUMENTATION-CENSUS.md` | Informe principal: método, hallazgos, estado | Markdown |
| `DOCUMENTATION-INVENTORY.tsv` | Inventario procesable: 1 fila por fuente documental | TSV, 20 campos |
| `DOCUMENTATION-TOPICS.md` | Vocabulario de temas + rutas de búsqueda | Markdown |
| `DOCUMENTATION-RELATIONSHIPS.md` | Relaciones documentales verificadas | Markdown |
| `DOCUMENTATION-GAPS.md` | Huecos, contradicciones, roturas, duplicados | Markdown |

---

## 1. Método

### 1.1 Descubrimiento primero, profundidad después

Se siguió el orden exigido: estructura → enumeración → tipos → índices → referencias →
primarios → profundizaciónselectiva.

| Fase | Qué se hizo | Resultado |
|---|---|---|
| Estructura | Recuento por directorio, extensión y tamaño | 1764 ficheros; 7 directorios de primer nivel |
| Enumeración | Los 256 `.md` con tamaño y ruta | Lista completa en el TSV |
| Tipos | Clasificación por extensión con excepción del bulk de `03-EXPERIMENTOS` | 1321Measurement artefacts vs 255 documentos |
| Índices | Lectura de `README.md`, `00-INDICE/README.md`, `AGENTS.md`, `DIAGRAMAS/README.md`, `10-NAVEGACION-DOCUMENTAL.md` | 5 mecanismos de navegación ya existen |
| Referencias | Extracción de enlaces Markdown, rutas en backticks y nombres `.md` desnudos; resolución contra el árbol real | 613 aristas resueltas, 140 candidatas a rotura |
| Profundización | Lectura de las cabeceras y primeros párrafos de los 256 `.md`; lectura completa de ~15 | Matriz de clasificación |
| Validación | Verificación de existencia de las 1576 rutas del TSV, parseo TSV, cobertura 256/256 `.md` | 0 rutas inexistentes, 0 malformations |

### 1.2 Criterio de "documentación"

**No se清单ó como documentación todo lo que no es Markdown.** El repositorio tiene 1764
ficheros; 1576 son `.md`, `.txt`, `.json`, `.csv`, `.tsv`, `.log`, `.lines`, `.sha256`. De esos:

- **255** son documentos redactados (persona o agente los escribió para ser leídos).
- **1321** son **artefactos de medición por corrida**: 690 `stdout.txt`/`state_initial.txt`/
  `state_final.txt`/`manifest.txt`, 384 `telemetry.csv`, 71 `.log`, etc. Son evidencia original,
  valuable pero **no son documentos**: no tienen intención narrativa y su función se describe
  desde el `.md` del experimento que los produjo.

Regla aplicada: un artefacto de medición se registra en el inventario con
`CATEGORY=RAW_EVIDENCE` y `PRIORITY=RAW_EVIDENCE`, y **no** se le asigna `PRIMARY_TOPIC`
propio salvo que tenga un tema identificable. La ruta hacia él pasa por el documento del
experimento.

### 1.3 Vocabulario de estado usado

- **CATEGORÍA** (16 valores): `CURRENT_STATE`, `HISTORICAL_EVIDENCE`, `EXPERIMENT`,
  `EXPERIMENT_RESULT`, `ANALYSIS`, `HYPOTHESIS`, `DECISION`, `DESIGN`, `IMPLEMENTATION`,
  `PATCH`, `TEST`, `RECOVERY`, `STATUS`, `INDEX`, `EXTERNAL_SOURCE`, `REFERENCE`, `RAW_EVIDENCE`.
- **TEMPORALIDAD** (4 valores): `CURRENT`, `HISTORICAL`, `MIXED`, `UNKNOWN`.
- **PRIORIDAD** (4 valores): `PRIMARY`, `SECONDARY`, `TERTIARY`, `RAW_EVIDENCE`.

---

## 2. Resultado del censo

```
CENSUS=COMPLETO
DOCUMENTOS_REDACTADOS=255
ARTEFACTOS_MEDICION=1321
TOTAL_INVENTARIO=1576
```

### 2.1 Distribución por categoría (solo documentos redactados)

| Categoría | N | Lectura |
|---|---:|---|
| `DESIGN` | 65 | Diseños de fases E–Q, de ideas I-01..I-10 y del workload sintético. **Ninguno es evidencia.** |
| `ANALYSIS` | 71 | Auditorías, reconciliaciones, addenda, matrices. Mezcla de disco viejo y nuevo. |
| `EXPERIMENT_RESULT` | 28 | Resultados y bitácoras de experimento. Todos `HISTORICAL`. |
| `EXPERIMENT` | 15 | Protocolos y planes previos a la ejecución. Todos `HISTORICAL`. |
| `STATUS` | 13 | Estados y releases. Concentrados en la raíz. |
| `INDEX` | 21 | Índices, mapas y las 16 vistas de `DIAGRAMAS/`. |
| `RECOVERY` | 12 | Preflight C1, TTY, recovery y los 3 documentos de `PATCH-RECOVERY/`. |
| `IMPLEMENTATION` | 8 | `rx550-torneo` por fases, H12-1/2, código C1. |
| `EXTERNAL_SOURCE` | 10 | FASE R-0 y benchmarks externos. |
| `HYPOTHESIS` | 3 | `HYPOTHESIS-REGISTER`, `hypotheses.md`, `rejected_ideas.md`. |
| `DECISION` | 3 | `decisions.md`, `DECISIONES-D1-D10.md`, `experiments_proposed.md`. |
| `REFERENCE` | 3 | `AGENTS.md`, `IMPLEMENTATION-SAFETY-RULES.md`, `ESTADOS-ES-EN.md`. |
| `TEST` | 2 | `TESTING.md`, `README-FASE2/3` (tests de write controlado). |
| `PATCH` | 1 | `PATCH-REGISTRY-FINAL.md`. |
| `RAW_EVIDENCE` | 1321 | Artefactos de medición + 2 JSON de auditoría. |

### 2.2 Distribución por temporalidad — **el hallazgo estructural más importante**

| Temporalidad | N (docs) | N (total filas) |
|---|---:|---:|
| `HISTORICAL` | 189 | 1445 |
| `MIXED` | 50 | 111 |
| `CURRENT` | 16 | 16 |
| `UNKNOWN` | 0 | 4 |

**Solo 16 documentos son `CURRENT`.** Todo lo demás describe el host anterior. Esto es coherente
con lacronología del proyecto (el grueso de la investigación se hizo en el disco viejo, Nobara
44/kernel 7.2.x, y la consolidación del 2026-09-25 Lelvó al nuevo), pero tiene una consecuencia
operativa directa: **cualquier consulta sobre el estado actual del host debe resolverse en
`README.md`, `PROBLEM-STATUS-FINAL.md`, `PATCH-REGISTRY-FINAL.md`, `RELEASE-CANDIDATE.md`,
`FINAL-RELEASE-REPORT.md`, `INSTALL.md`, `ROLLBACK.md`, `TESTING.md`,
`RELEASE-EXCLUSIONS.md`, `CHANGELOG.md`, `01-AUDITORIA/PATCH-RECOVERY/*` y
`01-AUDITORIA/FINAL-VALIDATION/*`.**

### 2.3 Distribución por procedencia

| `SOURCE_STATUS` | N | Significado |
|---|---:|---|
| `HISTORICAL_OLD_DISK` | 1444 | Medido o redactado en el host anterior (fc44 / kernel 7.2.x). **No describe el host actual.** |
| `MIXED` | 110 | Documento de diseño o análisis que mezcla ambos contextos sin marcarlo. Riesgo de contaminación. |
| `CURRENT_NEW_DISK` | 16 | Redactado o medido en el disco actual. |
| `CURRENT_NEW_DISK_STALE_HOST` | 2 | `FINAL-VALIDATION-*.{md,json}`: capturados en el disco nuevo, pero **el host ya cambió después**. |

---

## 3. Mecanismos de navegación que YA existen

No se creó nada nuevo porque ya hay cinco capas. Se documentan aquí para que el diseño futuro
decida si las reutiliza, las corrige o las sustituye.

| # | Mecanismo | Ruta | Estado real | Limitación principal |
|---|---|---|---|---|
| 1 | Instrucciones de agente | `AGENTS.md` | Vigente, V2 | Declara 7 documentos "canonical"; el estado real está en otros 4 de la raíz |
| 2 | Índice canónico | `00-INDICE/README.md` | Vigente | "Cómo empezar" apunta a `MASTER-RESEARCH-STATUS`, que a su vez delega en un overlay |
| 3 | Estado único | `00-INDICE/MASTER-RESEARCH-STATUS.md` | Vigente con overlay | Se autocallifica "punto único de entrada", pero su overlay delega el estado en la raíz |
| 4 | Mapa documental | `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` | **`DRAFT/CONFLICT`** | El propio documento se marca no vivo |
| 5 | Vistas Mermaid | `00-INDICE/DIAGRAMAS/` (17 ficheros) | **`DRAFT/CONFLICT`** (16 de 17) | Sin jerarquía; son vistas, no índices |
| 6 | Registro de movimientos | `00-INDICE/REGISTRO-DE-MOVIMIENTOS.md` + `REGISTRO-DE-REPARACION-REFERENCIAS.md` | Histórico | Explica por qué hay referencias rotas |

**Sobre el punto 3:** `MASTER-RESEARCH-STATUS.md` (63 KB) contiene en su cabecera un `OVERLAY
FINAL 2026-09-25` que remite a `PATCH-REGISTRY-FINAL.md`, `PROBLEM-STATUS-FINAL.md`,
`RELEASE-CANDIDATE.md` y `FINAL-RELEASE-REPORT.md`. Es decir: el "estado único" ya no contiene el
estado único. Esto es correcto por diseño (el overlay es lo nuevo) pero **peligroso para un
navegador**: el documento con más referencias entrantes (30) ya no es la fuente de estado. Un
router que empiece por `MASTER-RESEARCH-STATUS.md` darüber will deliver a un lector el estado
histórico, no el vigente.

---

## 4. Las 16 fuentes `CURRENT` (índice de entrada rápida)

Estas son, y solo estas, las que describen el disco actual.

| # | Documento | Responde a |
|---:|---|---|
| 1 | `README.md` | ¿En qué estado está el proyecto? ¿Qué leo primero? ¿Qué está prohibido? |
| 2 | `PROBLEM-STATUS-FINAL.md` | ¿Cuál es el estado de cada problema? (22 filas) |
| 3 | `PATCH-REGISTRY-FINAL.md` | ¿Qué correcciones existen, con qué hash y cómo se revierten? |
| 4 | `RELEASE-CANDIDATE.md` | ¿Se puede publicar? ¿Qué gates faltan? |
| 5 | `FINAL-RELEASE-REPORT.md` | ¿Qué se demostró y qué no? ¿Qué bloquea? |
| 6 | `RELEASE-EXCLUSIONS.md` | ¿Qué no debe subirse nunca? |
| 7 | `INSTALL.md` | ¿Cómo se instala y qué selectores se usan? |
| 8 | `ROLLBACK.md` | ¿Cómo se revierte sin cambios persistentes? |
| 9 | `TESTING.md` | ¿Qué pruebas existen y qué criterios aceptan? |
| 10 | `CHANGELOG.md` | ¿Qué cambió en la consolidación? |
| 11 | `01-AUDITORIA/PATCH-RECOVERY/PATCH-RECOVERY-REPORT.md` | ¿Qué parches se recuperaron y cuáles no? |
| 12 | `01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md` | ¿Cada parche es recuperable, aplicable y riesgoso? |
| 13 | `01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md` | ¿De dónde salió cada parche? ¿Qué se buscó y no se encontró? |
| 14 | `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.md` | Captura de host, GPU, paquetes, renderers, PM/DPM, firmware. **Host obsoleto.** |
| 15 | `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json` | Ídem, legible por máquina |
| 16 | `01-AUDITORIA/FASE-VFIO-PASSTHROUGH/VFIO-FEASIBILITY-AUDIT-20260925T132242Z.{md,json}` | ¿Es viable VFIO? ¿Qué bloquea? |

Los 5 ficheros de esta fase (`DOCUMENTATION-CENSUS/`) son `CURRENT` por construcción pero no se
autoincluyen en la tabla para no contaminar el censo con su propia salida.

---

## 5. Las tres identidades de host que coexisten en la documentación

Este es el punto que más cuidado requiere y por eso va aquí, no solo en `DOCUMENTATION-GAPS.md`.

| Contexto | SO | Kernel | Mesa | RX550 en | Fuente |
|---|---|---|---|---|---|
| **Disco viejo** (historia de la investigación) | Nobara 44 | `7.2.4` / `7.2.6` | 26.2.2 / 26.2.3 | `card1` | ~1444 documentos, `P0-EXPERIMENTAL-VALIDITY-GATE`, `knowledge.md`, `C1-PREFLIGHT-*`, `COUNTERS-ASIC-*` |
| **Disco nuevo, captura del 2026-09-25T13:58Z** | Nobara 43 | `6.18.2-200.nobara.fc43` | 25.3.2 | `card2` | `FINAL-VALIDATION-*`, `README.md`, `PATCH-REGISTRY-FINAL.md`, `PROBLEM-STATUS-FINAL.md` |
| **Host vivo, medido el 2026-09-25T22:22Z** | Nobara 44 | `7.1.3-200.nobara.fc44` | 26.2.3 | `card1` | `PATCH-RECOVERY/PATCH-SOURCES.md` §3 |

Consecuencias verificadas, sin interpretar causa:

1. `FINAL-VALIDATION-*` **no describe el host vivo**. Está marcado
   `SOURCE_STATUS=CURRENT_NEW_DISK_STALE_HOST` en el inventario.
2. El host vivo (`7.1.3`) tiene un kernel **más antiguo** que el que usaba el disco viejo
   (`7.2.4`/`7.2.6`). No es "el host viejo con una actualización".
3. La numeración `cardN` de la RX550 cambió de `card2` (captura) a `card1` (vivo). El PCI
   `1002:699f` y el BDF `0000:01:00.0` no cambiaron.
4. `mesa-vulkan-drivers` **no está instalado** en el host vivo, sí lo estaba en las capturas.
5. Ningún documento de la raíz (`README.md` incluido) refleja la identidad del host vivo.

---

## 6. Vocabulario de temas

Se buscaron los 57 topics exigidos más los discovered. Cobertura real (documentos redactados):

| Tema | N docs | Hay fuente primaria |
|---|---:|---|
| RX550 / GPU / AMDGPU / POLARIS12 / GFX8 / DRM | 60–190 | Sí, pero mayoritariamente histórica |
| EXPERIMENTS / EXPERIMENT_RESULT | 169 | Sí (`RESEARCH.md`, `MASTER-RESEARCH-STATUS.md`) |
| KERNEL / FIRMWARE / DRIVER | 41–137 | Solo histórica |
| MESA / RADV / VULKAN / OPENGL | 53–149 | Sí, con conflicto de versión |
| DPM / SCLK / MCLK / POWER_CAP / RUNTIME_PM | 43–128 | Sí, histórica |
| SYSTEMD / KALM / AUTOPILOT / IRQ / GOVERNOR | 31–112 | **No** — el host viejo ya no tiene esas unidades |
| C1 / OWNERSHIP / RECOVERY / TTY / D_STATE | 16–88 | Sí (diseño) |
| KWIN / WAYLAND / XWAYLAND / INTEL_GPU | 26–69 | Parcial, histórica |
| BENCHMARKS / SUPERPOSITION / GLMARK2 / M1 / R4B / R4C | 6–115 | Sí |
| PATCHES / RELEASE / GITHUB / SECURITY / REPRODUCIBILITY | 24–99 | Sí, y son los `CURRENT` |
| VRAM / COUNTERS / TELEMETRY / SMU / FRAME / WSI | 26–124 | Sí |
| BTRFS / HDD / STORAGE / SMART / IO / PSI | 15–56 | Histórica; Btrfs en `CONFLICT` |
| VFIO / IOMMU | 4–14 | Sí, `CURRENT` (una auditoría) |
| BACO | 8 | Solo menciones; **sin fuente primaria dedicada** |
| FIREFOX | 5 | Solo menciones; **sin fuente primaria dedicada** |
| UDEV / GRUB | 11–34 | Solo "no tocar"; **sin fuente primaria** |

Detalle completo y rutas de búsqueda en `DOCUMENTATION-TOPICS.md`.

---

## 7. Referencias cruzadas

```
Aristas文档→documento resueltas:  613
Nodos Markdown sin referencia entrante:  59 de 256
Candidatas a referencia rota:  140
  ├─ REAL_BROKEN (no resuelve en el árbol): 140
  ├─ EXTERNAL_SOURCE (fichero de Mesa/kernel): 31
  ├─ EXTERNAL_SYSTEM (ruta /usr, /etc, /opt): 22
  ├─ ARTEFACTO de mi propio regex: 21  (descartados)
  └─ AMBIGUOUS (nombre desnudo, >1 candidato): 4
```

El detalle y la clasificación de las 140 están en `DOCUMENTATION-RELATIONSHIPS.md` y
`DOCUMENTATION-GAPS.md`. **No se reparó ninguna**: la fase lo prohíbe.

Los 59 documentos sin referencia entrante no están necesariamente huérfanos: los resultados de
experimento se consultan por ruta conocida, no por enlace. La lista está en el informe de
relaciones.

---

## 8. Clasificación de los no-Markdown

| Tipo | N | Función real | ¿Documentación? |
|---|---:|---|---|
| `.txt` en `runs/` y `results/` | 690 | Salida de proceso, estado pre/post, manifest de corrida | No. `RAW_EVIDENCE` |
| `.csv` de telemetría | 384 | Series temporales por corrida (10 Hz) | No. `RAW_EVIDENCE` |
| `.tsv` | 106 | Igual que `.csv` | No. `RAW_EVIDENCE` |
| `.log` | 71 | Log de journal/kernel de una corrida | No. `RAW_EVIDENCE` |
| `.json` de auditoría | 15 | Captura estructurada de preflight/VFIO/validación | **Sí**, como fuente primaria de datos |
| `.json` de experimento | 41 | Métricas y auditorías por corrida | No. `RAW_EVIDENCE` |
| `.lines` / `.sha256` | 13 | Volcado de líneas de log / digest | No. `RAW_EVIDENCE` |
| `.sh` / `.py` / `.c` / `.cpp` / `.h` | 67 | Código, no documentación | No. Excluido del inventario documental |
| `.o` / `.so` / `.spv` / `.bin` / `.run` | 15 | Artefactos de compilación | No. Excluido |
| `.pyc` / `.cmake` / `.ninja*` | 30 | Residuos de build | No. Excluido |

**Nota sobre `RX550_BUILD_SPECIFICATION.txt`:** `00-INDICE/README.md` lo ofrece como
especificación técnica de 45 secciones, pero es un `.txt` y por tanto no entró en el inventario
documental. Es un documento de arquitectura real. Consta en `DOCUMENTATION-GAPS.md` como
**documento no-Markdown con función documental**.

---

## 9. Lo que este censo NO pudo determinar

1. **Si las 140 referencias rotas son errores o historia.** Muchas apuntan a ficheros del host
   viejo (`kalmd.py`, `kalm-lite.py`, `/usr/local/bin/system-autopilot.sh`) que nunca estuvieron
   en el repo. Requiriría leer el contexto de cada una; se clasificaron pero no se juzgaron.
2. **Qué documentos `MIXED` contaminan estado actual con histórico.** 110 documentos mezclan
   ambos contextos. `DOCUMENTATION-GAPS.md` los lista; auditoría línea a línea requeriría otra fase.
3. **Si las 16 vistas `DRAFT/CONFLICT` de `DIAGRAMAS/` contienen información que no existe en
   ningún texto.** Probablemente no, pero no se verificó vista por vista.
4. **Veracidad de las afirmaciones de los 1321 artefactos de medición.** No se revalidó ninguna
   cifra; se clasificó su función, no su corrección.
5. **Qué parte de `03-EXPERIMENTOS/` es publicable.** Depende de `RELEASE-EXCLUSIONS.md` y de la
   revisión de seguridad pendiente; fuera del alcance de esta fase.

---

## 10. Consecuencias para el diseño del router (sin diseñarlo)

Observaciones que la fase siguiente necesitará, derivadas del censo:

1. **La mayoría de los documentos son históricos y el router no lo dice.** Sin un mecanismo
   explícito de temporalidad en la primera línea de respuesta, el riesgo de citar el disco viejo
   como estado actual es alto: 1444 de 1576 filas son `HISTORICAL`.
2. **Hay dos "estados únicos" y gana el equivocado por número de referencias.**
   `MASTER-RESEARCH-STATUS.md` (30 entrantes) frente a `PROBLEM-STATUS-FINAL.md` (15) +
   `PATCH-REGISTRY-FINAL.md` (14) + `RELEASE-CANDIDATE.md` (11) + `FINAL-RELEASE-REPORT.md` (11).
3. **Cuatro documentos son conflictivos entre sí sobre el mismo hecho** (C1 tests, Mesa,
   kernel, Btrfs). Un router por intención debe poder devolver "hay conflicto, consulta X e Y".
4. **Dos temas del vocabulario exigido no tienen ninguna fuente primaria**: `BACO` y `FIREFOX`
   aparecen en 8 y 5 documentos respectivamente, siempre de paso.
5. **`UDev`, `GRUB` y `UDEV` solo existen como prohibición**, no como documentación. Si alguien
   pregunta "¿cómo configuro udev?", la respuesta correcta es "no hay fuente; y está prohibido".
6. **El 51 % de las filas del inventario son artefactos sin documento padre claro.** La ruta
   desde un tema hasta su evidencia necesita el dato `EXPERIMENT_DIR` del TSV, que no existe
   todavía como columna.
7. **Existe un mechanism de navegación maduro y declarado no vivo** (`R2-GLOBAL-DOCUMENTATION-MAP.md`
   + 16 diagramas). Reutilizar su taxonomía es más barato que inventar una nueva, pero exige
   resolver antes su estado `DRAFT/CONFLICT`.

---

## 11. Hashes de los informes de esta fase

Se registran en `DOCUMENTATION-GAPS.md` §8 tras el cálculo final, junto con el resultado de la
validación de integridad.

---

## 12. Validación ejecutada

| Comprobación | Resultado |
|---|---|
| Cada ruta del TSV existe en disco | **1576/1576** |
| Rutas inventadas | **0** |
| TSV parseable (`csv.DictReader`, tab) | **Sí**, 1576 filas, 20 campos, 0 malformations |
| Consistencia de número de campos por línea | **1577/1577** correctas |
| Cobertura Markdown | **256/256** |
| `.md` en el TSV que no existe en disco | **0** |
| Relaciones apuntan a documentos reales | 613 aristas `OK` verificadas; las `REAL_BROKEN` están aisladas y catalogadas |
| Cada tema tiene fuentes reales | Sí; 2 temas sin primaria registrados como hueco |
| Archivos modificados fuera de `01-AUDITORIA/DOCUMENTATION-CENSUS/` | **0** |
| Commit / push / remote | **0** |
| Cambio de sistema | **0** |

Verificación de no-efecto: `git status --short` muestra únicamente los 5 ficheros nuevos de este
directorio como `??`. El índice con 360 rutas preparadas de la fase de parches permanece
intacto; `HEAD` sigue en `c6146788e0d4fb12d9b0ec1209fa2840692de0c5`.
