# R1-NORMATIVE-INVENTORY-AND-UMBRELLA-REMOVAL-20260926

`DOCUMENT_KIND` = `NORMATIVE_INVENTORY` + `UMBRELLA_REMOVAL` · **READ_ONLY + DOCUMENTACIÓN**
`TECHNICAL_MODEL_STATUS` = `CLOSED` — **sin modificar**
`PROJECT_MAPPING` = `NOT_ATTEMPTED` · `ANY_ALL` = `NOT_DECIDED` · `PASS_FAIL` = `NOT_DEFINED`
`HUMAN_MIXED_TERM` = `RETIRED / NO_INTERPRETAR` · `REQUIREMENT_INTENT_RECONSTRUCTION` = `NOT_ATTEMPTED`
Sin código productivo, tests, `AGENTS.md`, `README.md`, runtime, sudo, systemctl, C1, benchmarks,
sysfs/GPU/PM/storage ni commits.

**Este documento es una corrección metodológica de una especificación mezclada. No es una
afirmación sobre qué «realmente quiso decir» el humano.** La intención no se investiga y no se
reconstruye.

## 0 · FUENTES INVENTARIADAS (procedencia antes que contenido)

| Documento | sha256 | Estado | Papel |
|---|---|---|---|
| `R1-G1-G2-DECISION-REQUEST-20260926.md` | `2468074d` | `HISTORICAL` | 4 **alternativas** de objeto para `ATTRIBUTABLE` (A–D) + G-2 |
| `R1-ATTRIBUTION-DECOMPOSITION-MODEL-20260926.md` | `a3a627b2` | `HISTORICAL` (con §1 marcado `INVALIDATED` por esta ronda) | 8 propiedades `P1…P8` ya descompuestas |
| `R1-ATTRIBUTABLE-NODE-ROWS-REQUIREMENT-20260926.md` | `7ddbb92f` | `HISTORICAL` | procedencia explícita: `HUMAN_REQUIREMENT` / `AGENT_FORMALIZATION` (`F-1…F-6`) / `EXTERNAL_SPEC` / `INFERENCE` |
| `R1-NORMATIVE-REQUIREMENT-DECOMPOSITION-20260926.md` | `134b6f3b` | `VIGENTE` | registro `N-1…N-10`, 10 campos por propiedad |

**No se aggregated propiedades nuevas**: el registro `N-1…N-10` ya cubre `P1…P8` uno a uno
(`NODE_COMPLETENESS`, `NODE_PCI_IDENTITY`, `DRM_FD_VISIBILITY`, `DRM_FILE_IDENTITY`,
`PROCESS_ASSOCIATION`, `PCI_DEVICE_ASSOCIATION`, `PASID_VM_PROCESS_RELATION`,
`MEMORY_USAGE_ATTRIBUTION`, `ENGINE_USAGE_ATTRIBUTION`, `OWNERSHIP_VERDICT`). El inventariar
consiste en **cotejar** esos tres documentos contra ese registro, no en crear un cuarto.

## 1 · FASE 1 — INVENTARIO NORMATIVO

`REQUIRED_BY_HUMAN` se conserva estrictamente: `YES` solo con cita literal del texto humano;
`NO` solo si el texto humano **no** la nombra; `UNKNOWN` cuando el puente es el término retirado.

| PROPERTY_ID | NAME | DEFINITION | TARGET_ENTITY | UNIT | REQUIRED_BY_HUMAN | PROVENANCE | CURRENT_STATUS | PASS_SEMANTICS | FAIL_SEMANTICS | UNKNOWN_SEMANTICS | FALSIFICATION_CONDITION |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **N-1** | `NODE_COMPLETENESS` | el universo requerido de nodos fue observado con la cobertura exigida | nodo DRM | nodo | **YES** — «complete», «FD visibility is incomplete» (`AGENTS.md:176`, `:180`) | `HUMAN_REQUIREMENT` | `IMPLEMENTED`, `PROJECT_REQUIREMENT UNRESOLVED` | no definida: la cobertura se **reporta**, no se puntúa | no definida | universo no enumerable; PID desaparecido sin ausencia demostrada | mismo universo y privilegio con las 4 condiciones satisfechas y una fila de FDs ausente |
| **N-2** | `NODE_PCI_IDENTITY` | el nodo puede vincularse al dispositivo PCI RX550 requerido | nodo/dispositivo | dispositivo | **YES** — «identified by PCI identity rather than by node name» | `HUMAN_REQUIREMENT` | `IMPLEMENTED`, `PROVEN` en captura | no definida | no definida | BDF no resoluble; `dev_is_pci` falso | `drm-pdev` emitiendo algo que no sea `domain:bus:slot.func` |
| **N-3** | `DRM_FD_VISIBILITY` | los DRM FDs del universo requerido pudieron observarse **y leerse** | FD DRM / proceso | FD | **YES** (parcial) — «FD visibility», «root namespaces are not covered» | `HUMAN_REQUIREMENT` | `IMPLEMENTED`, `OBSERVED` (12 FDs / 4 procesos) | no definida | no definida | fdinfo ilegible; fd de destino irresoluble | `read_bytes` en error convertido en ausencia (hoy protegido por guard) |
| **N-4** | `DRM_FILE_IDENTITY` | se observó un `drm-client-id`; **qué unidad representa** | `struct drm_file` | un `drm_file` | **UNKNOWN** — único puente: la palabra `client`, **retirada** | `HUMAN_REQUIREMENT_VIA_AMBIGUOUS_TOKEN` | `PARTIAL`: solo `PRESENCE`; `VALUE = NOT_AVAILABLE` | no definida | no definida | clave ausente **o** valor no preservado | dos `drm_file` con el mismo `drm-client-id` |
| **N-5** | `PROCESS_ASSOCIATION` | qué proceso está asociado al `drm_file` según la fuente utilizada | relación `drm_file` ↔ proceso | relación | **NO por su cuenta**; la dirección inversa (FD→proceso) sí tiene antecedente | `TECHNICAL_MODEL` | `NOT_IMPLEMENTED` (carrier debugfs existe en el core) | no definida | no definida | `drm_clients_info` sin columna `tgid` | `drm_clients_info` sin columna `tgid`, o `drm_file.h:272` describiendo al proceso original |
| **N-6** | `PCI_DEVICE_ASSOCIATION` | qué dispositivo DRM/PCI corresponde al file observado | `drm_file`/minor/device ↔ PCI | relación | **NO** | `TECHNICAL_MODEL` | `PARTIAL`: contador `drm-pdev` **pooled**, no relación por file | no definida | no definida | `drm-pdev` ausente (dispositivo no-PCI) | dos `drm_file` del mismo dispositivo con `drm-pdev` distinto |
| **N-7** | `PASID_VM_PROCESS_RELATION` | qué relación con VM/PASID/proceso puede establecerse **si la evidencia lo permite** | vmid / VM / proceso | vmid | **NO** — el texto no menciona PASID | `AGENT_FORMALIZATION` | `SOURCE_INCOMPLETE` | no aplicable: no hay fuente | no aplicable | `SOURCE_INCOMPLETE` (no es ausencia) | `pasid` impreso junto a un PID sin fault concurrente |
| **N-8** | `MEMORY_USAGE_ATTRIBUTION` | qué estadísticas de memoria están asociadas al `drm_file` | `drm_file` | agregado por `drm_file` y región | **NO** | `AGENT_FORMALIZATION` | `NOT_IMPLEMENTED` (0 referencias en el collector) | no aplicable | no aplicable | `NOT_OBSERVED`; `=0` no prueba no-uso | clave de memoria indexada por proceso en la spec |
| **N-9** | `ENGINE_USAGE_ATTRIBUTION` | qué actividad de engine está asociada al cliente | `drm_file` × engine | `drm_file` × engine | **NO** | `AGENT_FORMALIZATION` | `NOT_IMPLEMENTED` (0 referencias) | no aplicable | no aplicable | `NOT_OBSERVED`; no monótona | `drm-engine-*` por proceso, o declarada monótona |
| **N-10** | `OWNERSHIP_VERDICT` | veredicto compuesto | consumidor del proyecto | veredicto | **UNKNOWN** — el texto que lo define usa un término **retirado** | `HUMAN_REQUIREMENT` (defectuoso) | `PARTIAL`; `OWNERSHIP = UNKNOWN` | **no definida**: el agregado no puede ser `FULL` con fila abierta (verificado por test) | no definida | `REQUIREMENT_UNRESOLVED` | matriz con 3 filas, o con `PASS` en fila sin evidencia → la suite lo detecta |

**Nada recibe `PASS`/`FAIL` normativo.** Las columnas de semántica quedan `no definida` porque
definirlas es la decisión humana que esta ronda no toma.

### 1.1 · Elementos de los documentos fuente que **no** son propiedades

| Elemento | Clasificación | Motivo |
|---|---|---|
| Alternativas A–D de `R1-G1-G2` (`ATTRIBUTION_TO_DRM_CLIENT` / `_PROCESS` / `_PCI_NODE` / `_OBSERVED_FD`) | **`HISTORICAL_ONLY`** | son **opciones de objeto** que se historiesaron al retirar el término; ninguna elegida. Mapear a propiedades separadas: A→N-4/N-5, B→N-5, C→N-2/N-6, D→N-3 |
| G-2 «ubicación del requisito proceso↔FD» | `HISTORICAL_ONLY` | pregunta de diseño ya superada por la separación FD→proceso (N-3) vs `drm_file`→proceso (N-5) |
| `F-1`…`F-6` | **`AGENT_FORMALIZATION`** | las 11 filas, el texto de fila, la tupla de 3 campos y los umbrales `all()`/`any()` fueron creations del agente. `F-5` consta **sin justificación escrita** |
| `C-3` | `CONFLICT_UNRESOLVED` | Alternative A vs B: el objeto de `ATTRIBUTABLE` no fue determinado. Retirado el término, la pregunta queda sin objeto |

## 2 · FASE 2 — SEPARACIÓN (confirmada, no modificada)

Las 10 propiedades de §1 son **independientes por construcción**: cada una tiene entidad, unidad,
fuente y falsificador propios, y ninguna se deriva de otra. Verificado en la ronda previa:
`TECHNICAL_MODEL` con 17 propiedades y 0 agregadas; `N-1…N-10` con 10/10 los 9 campos.

Las siete separaciones exigidas están cubiertas: nodo observable → **N-1**; identidad PCI →
**N-2** + **N-6** (el nodo y el file son direcciones distintas, no la misma propiedad);
FD↔proceso → **N-3**; identidad `drm-client-id` → **N-4**; `drm-client-id` ↔ `drm_file` → la
**misma unidad** de N-4, explícitamente *cardinalidad* (FD→`struct file` N:1 por `dup()`/`fork()`;
`struct file`→`drm_file` 1:1) separada del *valor*; proceso ↔ cliente → **N-5**; memoria → **N-8**;
engine → **N-9**; VM/PASID → **N-7**. Bajo `attributable` **no queda ninguna propiedad oculta**: las
entidades del core (FD, `struct file`, `drm_file`, `client-id`, `pdev`, minor, `drm_device`,
PID/TGID, master, GEM, memory, engine, VM, PASID, page-fault `client-id`) tienen cada una su fila en
el modelo cerrado, y las que siguen sin fuente están `SOURCE_INCOMPLETE` **explícitamente**, no
ocultas.

## 3 · FASE 3 — CAPAS SEPARADAS

| Capa | Qué dice esta ronda | Qué **no** dice |
|---|---|---|
`HUMAN_REQUIREMENT` | 3 propiedades con cita literal (N-1, N-2, N-3); 1 con puente retirado (N-4); 1 defectuosa (N-10) | que el resto sea exigido |
`AGENT_FORMALIZATION` | N-7, N-8, N-9; las alternativas A–D; `F-1…F-6`; los 10 nombres `N-*` | que sean requisitos |
`TECHNICAL_SEMANTICS` | 17 propiedades, `CLOSED`, sin modificar | nada normativo |
`OBSERVABILITY` | por propiedad: `EXPOSED` / `NOT_EXPOSED` / `NOT_OBSERVED` / `ACCESS_DENIED` / `SOURCE_INCOMPLETE` | que un `EXPOSED` esté leído |
`EVIDENCE` | `PRESENCE` de `drm-client-id` (por cita); `VALUE = NOT_AVAILABLE` | que pruebe la propiedad |
`PROJECT_VERDICT` | `OWNERSHIP = UNKNOWN` | ningún `PASS`/`FAIL` |

`ANY_ALL = NOT_DECIDED` y `PASS_FAIL = NOT_DEFINED` en las 11 apariciones de la capa normativa.

## 4 · FASE 4 — ELIMINACIÓN DEL PARAGUAS (clasificada, sin reemplazo ciego)

| Aparición | `CLASS` | Explicación |
|---|---|---|
| `attributable` en `AGENTS.md:176` | **`HISTORICAL_ONLY` (documento de entrada)** | frase humana original. No se edita `AGENTS.md`. Es el objeto de la corrección, no una propiedad |
| `attributable` en la descripción de la fila «FD table complete and attributable» | **`REPLACE_WITH_SEPARATE_PROPERTIES`** | «complete» → N-1/N-3; «attributable» → **se elimina**: no hay propiedad que lo sustituya, porque era la unión de N-4, N-5, N-6, N-7, N-8, N-9 |
| `DRM_ATTRIBUTION_FIELDS = ("drm-client-id","drm-pdev","pasid")` | **`RETIRE`** | eliminado del collector. Los tres campos **no** se sustituyen por un conjunto: pasan a N-4 (`client-id`), N-6 (`pdev`), N-7 (`pasid`), cada uno con su unidad |
| umbral `all()` sobre los 3 campos (`F-4`) | **`RETIRE`** | `ANY_ALL` no se hereda. Sin justificación escrita que preservar |
| umbral `any()` en las filas de nodo (`F-5`) | **`RETIRE`** | «basta uno, sin justificación escrita» es exactamente el tipo de regla que el término paraguas ocultaba |
| `card_clients` / `render_clients` | **`REPLACE_WITH_SEPARATE_PROPERTIES`** | contaban FDs; el nombre afirmaba clientes. Reemplazados por conteos **de FD** explícitos y por N-4 como propiedad de valor (aún `NOT_AVAILABLE`) |
| `ATTRIBUTION_TO_DRM_CLIENT` / `_PROCESS` / `_PCI_NODE` / `_OBSERVED_FD` | **`HISTORICAL_ONLY`** | alternativas de objeto no elegidas. Mapeo a N-4/N-5, N-5, N-2/N-6, N-3 |
| `DEBUGFS_CLIENT_ATTRIBUTION` | **`RETAIN_AS_TECHNICAL_TERM`** | nombre de campo del collector que describe un **recurso del kernel** (`debugfs/dri/<minor>/clients`), cuya semántica está `SOURCE_LOCATED` en `drm_debugfs.c:143`. No es un paraguas: es el nombre de una fila del fichero `clients` del core |
| `drm_client_debugfs_init` / `DRM_CLIENT_DEBUGFS_FACILITY` | **`RETAIN_AS_TECHNICAL_TERM`** | símbolo del kernel cuyo nombre contiene `CLIENT` heredado del dominio. Semántica `SOURCE_INCOMPLETE` |
| `drm-client-id` | **`RETAIN_AS_TECHNICAL_TERM`** | clave de la spec, 1:1 con `struct drm_file` |
| `attributable` en `ATTRIBUTABLE_*` (6 documentos) y `R1-ATTRIBUTION-DECOMPOSITION-MODEL` | **`HISTORICAL_ONLY`** | preservados como evidencia del defecto. `1 · CURRENT_ATTRIBUTION_MODEL` de ese documento queda **`INVALIDATED`** por esta ronda: describía un modelo que ya no existe |
| `attributable` en el collector | **`RETIRE`** | ausente. Verificado por test (`test_no_umbrella_attribution_identifier_in_code`): los 7 identificadores paraguas, 0 en código |

**Sin reemplazos ciegos**: cada entradaNombrada en la capa que le corresponde, o marcada
`HISTORICAL_ONLY` con su motivo.

## 5 · FASE 5 — RELACIÓN ENTRE LAS PROPIEDADES SEPARADAS

Determinar la **forma** de la relación es un hecho estructural; **elegir la conjunción** es decisión
humana. Lo primero sí se establece; lo segundo no.

| Relación observada | Tipo | Evidencia |
|---|---|---|
| N-4 ↔ N-6 (`client-id` ↔ `pdev`) | **acumulativa posible**: la spec dice que si la unicidad es por dispositivo, `drm-pdev` debe estar presente (`spec :70-71`) | `EXTERNAL_SPEC` |
| N-3 → N-4 (`FD` → `drm_file`) | **condicional**: sin FD legible no hay fila que caracterizar | `/proc` |
| N-5 ↔ N-4 | **independientes**: N-5 se lee por debugfs, N-4 por fdinfo; carriers distintos | `drm_debugfs.c:98-103` vs `drm_file.c:943` |
| N-8 ↔ N-9 | **independientes** y **no monotonas** | spec `:79-137`, `:140-175` |
| N-7 ↔ cualquiera | **independiente y no establecida**: `SOURCE_INCOMPLETE` | 0 en spec, 0 en core |
| N-1, N-2 | **independientes**: cobertura e identidad, fuentes distintas | `/proc` vs sysfs |
| N-10 | **consumidor**: depende de las anteriores, y la combinación **no** está establecida | `REQUIREMENT_UNRESOLVED` |

Consecuencia: **ninguna propiedad es requisito de otra** en sentido lógico, salvo la condición
documentada de la spec para N-4/N-6. No hay grupo que «satisface» a otro.

```
ANY_ALL = NOT_DECIDED
```
No se hereda `any()` ni `all()` del término retirado. `F-4` (los tres campos requeridos) y `F-5`
(basta uno, sin justificación) quedan **RETIRE**, no traducidos.

## 6 · FASE 6 — FORMA DEL RESULTADO

```
REQUISITO HUMANO ORIGINAL
        │  "complete attributable evidence" para card1/renderD129
        ▼
   TÉRMINO MEZCLADO: "attributable"
        │
        ▼
   RETIRED / NO_INTERPRETAR          (REQUIREMENT_AMBIGUOUS/DEFECTIVE)
        │
        ├── N-1 NODE_COMPLETENESS        ── SIGNIFICADO PROPIO ── OBLIGACIÓN DESCONOCIDA
        ├── N-2 NODE_PCI_IDENTITY         ── SIGNIFICADO PROPIO ── OBLIGACIÓN DESCONOCIDA
        ├── N-3 DRM_FD_VISIBILITY         ── SIGNIFICADO PROPIO ── OBLIGACIÓN DESCONOCIDA
        ├── N-4 DRM_FILE_IDENTITY         ── SIGNIFICADO PROPIO ── OBLIGACIÓN DESCONOCIDA
        ├── N-5 PROCESS_ASSOCIATION       ── SIGNIFICADO PROPIO ── OBLIGACIÓN DESCONOCIDA
        ├── N-6 PCI_DEVICE_ASSOCIATION    ── SIGNIFICADO PROPIO ── OBLIGACIÓN DESCONOCIDA
        ├── N-7 PASID_VM_PROCESS_RELATION ── SIGNIFICADO PROPIO ── FUENTE INCOMPLETA
        ├── N-8 MEMORY_USAGE_ATTRIBUTION  ── SIGNIFICADO PROPIO ── OBLIGACIÓN DESCONOCIDA
        ├── N-9 ENGINE_USAGE_ATTRIBUTION  ── SIGNIFICADO PROPIO ── OBLIGACIÓN DESCONOCIDA
        └── N-10 OWNERSHIP_VERDICT        ── CONSUMIDOR ── SIN CRITERIO VÁLIDO
```

**La separación es una corrección metodológica del requisito y de su formalización.** No afirma qué
«realmente quiso decir» el humano: afirma que el término no tiene unidad, y que sus componentes
tienen unidades distintas que deben decidirse por separado.

## 7 · FASE 7 — CRITERIO DE CIERRE

| # | Condición | Estado |
|---|---|---|
| 1 | ninguna propiedad normativa depende semánticamente de `attributable` | **CUMPLIDO** — 10/10 con definición propia; `attributable` no aparece como término de definición |
| 2 | cada propiedad tiene nombre propio | **CUMPLIDO** — 10 nombres únicos, 0 paraguas |
| 3 | cada propiedad tiene definición independiente | **CUMPLIDO** — `DEFINITION` + `TARGET_ENTITY` + `UNIT` por propiedad |
| 4 | procedencia separada | **CUMPLIDO** — `HUMAN_REQUIREMENT` (3) · `VIA_AMBIGUOUS_TOKEN` (1) · `TECHNICAL_MODEL` (2) · `AGENT_FORMALIZATION` (3) · defecto (1) |
| 5 | obligatoriedad explícita o `UNKNOWN` | **CUMPLIDO** — `YES` 3 · `NO` 3 · `UNKNOWN` 2 · defecto 1. Ninguna inventada |
| 6 | `PASS`/`FAIL` no inventado | **CUMPLIDO** — `PASS_FAIL = NOT_DEFINED`; todas las columnas de semántica `no definida` |
| 7 | ningún `ANY/ALL` heredado | **CUMPLIDO** — `ANY_ALL = NOT_DECIDED`; `F-4` y `F-5` `RETIRE` |
| 8 | `PROJECT_MAPPING` separado | **CUMPLIDO** — `NOT_ATTEMPTED` |
| 9 | `TECHNICAL_MODEL` sin modificaciones | **CUMPLIDO** — `ee86a3a7` / `0801b7d9` / `116f011e` sin cambio |
| 10 | sin código productivo modificado | **CUMPLIDO** — collector `458c9261f61b` sin cambio |

**FASE CERRADA.** Ninguna condición falla; no hay nada que corregir antes de avanzar.

## 8 · ESTADO

```
TECHNICAL_MODEL                   = CLOSED          (sin modificar)
NORMATIVE_INVENTORY               = CLOSED          (10 propiedades, 0 agregadas)
UMBRELLA_REMOVAL                  = CLOSED          (12 apariciones clasificadas)
HUMAN_MIXED_TERM                  = RETIRED / NO_INTERPRETAR
HUMAN_REQUIREMENT_STATUS         = MIXED/AMBIGUOUS_REQUIREMENT_CORRECTED_BY_DECOMPOSITION
REQUIREMENT_AMBIGUOUS             = DEFECTIVE (alias del estado canonico anterior)
REQUIREMENT_INTENT_RECONSTRUCTION = NOT_ATTEMPTED
PROJECT_MAPPING                   = NOT_ATTEMPTED
ANY_ALL                           = NOT_DECIDED
PASS_FAIL                         = NOT_DEFINED
REQUIREMENTS_ESTABLISHED          = 3  (N-1, N-2, N-3)   con cita literal
REQUIREMENTS_AGENT_FORMALIZATION  = 3  (N-7, N-8, N-9)   fuera del requisito humano
REQUIREMENTS_UNKNOWN              = 2  (N-4, N-10)
CODE_OR_TEST_CHANGES              = NONE
```
