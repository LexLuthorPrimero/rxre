# R1-TECHNICAL-MODEL-CLOSURE-20260926 · DEFINITIVO

`TECHNICAL_MODEL_STATUS` = **`CLOSED_WITH_DECLARED_LIMITS`**
`PROJECT_MAPPING` = **`NOT_ATTEMPTED`**
Documento de cierre. **No reescribe** los anteriores: los consolida y los marca.

`TEMPORALITY` = linux **v6.12** mainline, leído en esta sesión · `HOST_SCOPE` = ninguno
`WORKSPACE` = `/home/lucas/Escritorio/RX550-INVESTIGACION` · `staged` = 358 (preexistente) ·
`HEAD` = `df2406a` · **0 commits**

## 0 · Fuentes y artefactos

| Fuente primaria | Archivo | sha256 (prefijo) |
|---|---|---|
| `drivers/gpu/drm/drm_file.c` (996 L) | `drm_file.c` | leída, v6.12 |
| `include/drm/drm_file.h` | `drm_file.h` | leída |
| `drivers/gpu/drm/drm_lease.c` (733 L) | `drm_lease.c` | leída |
| `drivers/gpu/drm/drm_auth.c` (467 L) | `drm_auth.c` | leída |
| `include/drm/drm_gem.h` (637 L) | `drm_gem.h` | leída |
| `drivers/gpu/drm/drm_gem.c` (1535 L) | `drm_gem.c` | leída |
| `include/drm/drm_drv.h` (554 L) | `drm_drv.h` | leída |
| `drivers/gpu/drm/drm_internal.h` | `drm_internal.h` | leída |
| `include/drm/drm_lease.h` / `drm_auth.h` | ambos | leídos |
| `Documentation/gpu/drm-usage-stats.rst` (189 L) | `drm-usage-stats.rst` | leída |
| `drivers/gpu/drm/amdgpu/**` | — | **`SOURCE_INCOMPLETE`**: 404 en `raw.githubusercontent`, en la API de contenidos y en `kernel.org/doc` |

**Implementación verificada**:
`01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py`
sha256 `bf77c33255a3a65f6cb62387a6181020c7b96a1e1e009bbd49c8cde040558681` · suite **308 OK**.

## 1 · Mapa de documentos

| Documento | Estado | sha256 |
|---|---|---|
| **`R1-TECHNICAL-MODEL-CLOSURE-20260926.md`** (este) | **VIGENTE** | — |
| `R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md` | VIGENTE (§2properties) | `736ad20ab383` |
| `R1-RETIRED-NAMES-REGISTER-20260926.md` | VIGENTE (nombres retirados) | `4125ad49e7cf` |
| `R1-PROJECT-DEFECT-INVENTORY-20260926.md` | VIGENTE (plan de reparación) | `61629910d8d9` |
| `R1-TECHNICAL-SEMANTIC-MODEL-v3-20260926.md` | **SUPERSEDED** por este + el anterior | `8d92ec9b025b` |
| `R1-STEP2-PROPERTY-DEFINITIONS-20260926.md` | **SUPERSEDED** por §2 | `c739bdb02c5f` |
| `R1-SPEC-VERIFICATION-DEFECT-20260926.md` | **SUPERSEDED** (D-01 cerrado) | `dc2f62b25697` |
| `R1-D01-CLOSURE-20260926.md` | **SUPERSEDED** (D-01 cerrado) | `57b46e6d6f9c` |
| `R1-TECHNICAL-SEMANTIC-MODEL-20260926.md` (v1) | **HISTORICAL** | `7ed820ef0bbf` |
| `R1-TECHNICAL-SEMANTIC-MODEL-v2-20260926.md` | **HISTORICAL** | `35d86d1a9670` |
| `R1-G1-G2-DECISION-REQUEST-20260926.md` | **HISTORICAL** | `2468074d6d04` |

Ningún histórico fue reescrito. v1 y v2 conservan la afirmación de inmutabilidad que `D-01` corrigió:
es **evidencia histórica** y no debe leerse como estado actual.

## 2 · Entidades

| # | Entidad | Unidad | Identidad | Fuente | Límite |
|---|---|---|---|---|---|
| E-1 | `FD` | descriptor | ninguna DRM | VFS (fuera del árbol leído) | el path `/proc/<pid>/fd/<n>` **no distingue** dos `drm_file` |
| E-2 | `struct file` | un `struct file` | `private_data` | `drm_show_fdinfo` | **no expuesto** |
| E-3 | `struct drm_file` | **una apertura DRM** | sin identidad propia | `drm_file.h` | **no expuesto**; observable solo por las claves que lo resumen |
| E-4 | `drm-client-id` | un `drm_file` | `u64`, una vez en `drm_file_alloc` | `drm_file.c:142`; spec `:64-72` | unicidad **global o por dispositivo** (`C-4`) |
| E-5 | `drm-pdev` | un dispositivo PCI | **BDF** `domain:bus:slot.func` | `drm_show_fdinfo` | **constante por dispositivo**; no transporta vendor/device/class |
| E-6 | `drm_minor` | un nodo | (`index`, `type`) | `drm_file.h:77-87` | `cardN` no es identidad entre hosts |
| E-7 | `drm_device` | driver+dispositivo | `struct device` embebido | `drm_drv.h` | sin identidad DRM serial |
| E-8 | PCI device | un dispositivo | **BDF** | rama `dev_is_pci` | — |
| E-9 | `drm_file.pid` | un `task_struct` | **TGID** | `drm_file.c:143` | **no expuesto**; mutable |
| E-10 | `drm_master` | un master | `unique`, `magic_map`, `lessee_id` | `drm_lease.h`; `drm_lease.c` | **transferible** por leasing |
| E-11 | GEM object | un `drm_gem_object` | sin identidad observable | `drm_gem.h` | **no expuesto individualmente** |
| E-12 | memory statistics | agregado por `drm_file` | — | `drm_print_memory_stats`; spec `:143-172` | **por driver**; el core no la produce |
| E-13 | engine statistics | `drm_file` × engine | `<key>` por engine | spec `:79-133` | **por driver**; **no monótona** |
| E-14 | `driver_priv` | puntero opaco | **ninguna** en el core | `drm_file.h` | **`NOT_EXPOSED`**; contenido `SOURCE_INCOMPLETE` para amdgpu |
| E-15 | `VM` | — | — | — | **`SOURCE_INCOMPLETE`** |
| E-16 | `PASID` | un **vmid** | vmid | docs amdgpu | relación con proceso **episódica** |
| E-17 | GPU page-fault `client-id` | **bloque del motor** | — | — | **`SOURCE_INCOMPLETE`**; **no** es E-4 |

## 3 · Relaciones

| # | Relación | Cardinalidad | Condiciones | Mutabilidad |
|---|---|---|---|---|
| R-01 | FD → `struct file` | N:1 | siempre | refcount |
| R-02 | `struct file` → `drm_file` | **1:1** | si el driver implementa `open` DRM | inmutable |
| R-03 | FD ↔ `drm_file` | **N:1** | `dup`/`fork` | — |
| R-04 | `drm_file` → `client_id` | **1:1** | siempre | **inmutable en el core**; el campo es **público** (`drm_file.h:281-282`) y la spec **no** promete estabilidad |
| R-05 | `drm_file` → `drm_minor` | N:1 | siempre | inmutable |
| R-06 | `drm_minor` → `drm_device` | N:1 | siempre | inmutable |
| R-07 | `drm_device` → PCI device | 1:0:1 | **ssi** `dev_is_pci` | inmutable |
| R-08 | `drm_file` → PID/TGID | 1:1 (actual) | siempre | **mutable**, salvo `was_master` |
| R-09 | `drm_file` → `object_idr` | 1:N | siempre | mutable |
| R-10 | `drm_file` → `drm_master` | 1:0:1 | solo nodo primario; **transferible** | mutable |
| R-11 | `drm_file` → `driver_priv` | 1:1 | driver-defined | opaca |
| R-12 | `drm_file` → memory stats | 1:0:1 | **por driver** | derivado |
| R-13 | `drm_file` → engine stats | 1:0:N | **por driver** | **no monótona** |
| R-14 | `VM` → `PASID` | `UNKNOWN` | — | `SOURCE_INCOMPLETE` |
| R-15 | `PASID` → proceso | **1:0:1** | **solo durante un page fault Y con el proceso activo** | episódica |
| R-16 | `drm_file` → `driver_priv` → `amdgpu_fpriv` | `UNKNOWN` | — | **`SOURCE_INCOMPLETE`** |

**GEM ↔ múltiples `drm_file`**: un GEM object es alcanzable desde varios `drm_file` a través de
handles; el core **no declara** esa relación como identidad de proceso. `INFERENCE` por composición
de R-09 + R-08, **no** relación declarada.

## 4 · No-equivalencias (prohibidas, y comprobadas)

`drm-client-id` ≠ FD · ≠ PID · ≠ proceso · ≠ GPU page-fault `client-id` ·
`drm-pdev` ≠ identidad de cliente · `PASID` ≠ `drm-client-id` · ≠ PID · ≠ identidad permanente de
proceso · GEM object ≠ proceso · engine statistics ≠ proceso · ≠ actividad instantánea ·
memory statistics ≠ inventario de buffers · `drm-master` ≠ `drm-client-id`.

## 5 · Semántica establecida

- **`drm-client-id`** identifica conceptualmente un `struct drm_file` y sirve para distinguir FDs
  duplicados/compartidos (spec `:64-68`). Unicidad **global o por dispositivo**; en el segundo caso
  `drm-pdev` participa en la desambiguación (spec `:70-72`).
- **`drm-pdev`** describe el **PCI slot del dispositivo**. No identifica al cliente.
- **`drm_file.pid`** es el proceso que **está usando** el archivo. No es identidad histórica ni
  inmutable del opener; se reasigna salvo `was_master` (`drm_file.c` `drm_file_update_pid`;
  razón documentada en `drm_auth.c:215-242`).
- **`object_idr`** relaciona handles con objetos GEM. No convierte al GEM en identidad de proceso.
- **engine statistics** = tiempo que el engine pasó ocupado ejecutando workloads **de ese cliente**.
  Acumulado, **no monotónico**: ante un retroceso hay que retener el máximo.
- **memory statistics** = estadísticas **del cliente**, con categorías `total` (= private+shared),
  `shared`, `active`, `resident`, `purgeable`. `drm-memory-<region>` existe en la spec y **no** la
  emite el helper del core. No es inventario.
- **`drm-master`** = ownership/autenticación de nodos primarios, **transferible** por leasing.
- **page-fault `client-id`** (amdgpu) = **bloque del motor**. Entidad distinta de `drm-client-id`.
- **`PASID`** = vmid. Su relación con proceso es **condicional y episódica**.

## 6 · Observabilidad

`EXPOSED_BY_SYSTEM` → `READABLE_BY_ANALYZER` → `OBSERVED_IN_SAMPLE` → `PROVES_PROPERTY` →
`SATISFIES_PROJECT_REQUIREMENT`. Y `PRESENCE` → `VALUE` → `DISCRIMINATION` → `ATTRIBUTION`.
Ninguna capa implica la siguiente. "Expuesto" ≠ "leído" ≠ "demuestra la propiedad" ≠
"satisface el requisito".

`drm-client-id` ausente admite ≥7 causas, **dos de ellas indistinguibles** con la evidencia
disponible: *clave opcional no exportada* y *el driver no usa `drm_show_fdinfo()*.
`INDISTINGUISHABLE_FROM_AVAILABLE_EVIDENCE`. Ninguna ausencia se convierte en ausencia de propiedad.

## 7 · Properties cerradas en la implementación

| Nombre | Unidad | Predicate | Qué prueba | Qué NO |
|---|---|---|---|---|
| `DRM_FD_ENUMERATION` | FD | symlink resuelto a nodo DRM | ese FD apunta a un nodo | nada de clientes/PCI/proceso |
| `DRM_FDINFO_READABILITY` | FD | fdinfo leído no vacío | se pudo leer | que tenga clave alguna |
| `DRM_NODE_COMPLETENESS` | descriptor/proceso | los 4 términos de visibilidad | cobertura completa | **no** depende de fdinfo |
| `DRM_PCI_DEVICE_IDENTITY` | nodo | BDF+vendor+device+class+driver | el nodo es el dispositivo | nada de clientes |
| `DRM_CLIENT_ID_PRESENCE` | **FD** | clave presente | presencia | **no** identidad, **no** nº de clientes |
| `DRM_PCI_ADDRESS_PRESENCE` | **FD** | clave presente | el BDF que nombra | no discrimina clientes |
| `DRM_PASID_PRESENCE` | **FD** | clave presente | que el texto traía un vmid | no PID, no proceso |
| `PROCESS_ASSOCIATION` | `drm_file` / FD | `drm_file.pid` no expuesta; ruta `/proc` observable | tenedor actual del descriptor | no es el campo del núcleo |

## 8 · Correcciones históricas

| # | Afirmación previa | Estado actual | Evidencia que la corrige |
|---|---|---|---|
| 1 | "attributable" es una propiedad técnica | `HUMAN_REQUIREMENT_DEFECT · RESOLVED_BY_DECOMPOSITION` | un sintagma, ocho unidades distintas |
| 2 | `client_id`+`pdev`+`pasid` = una identidad | `REFUTED` | tres relaciones, tres dominios |
| 3 | nº de FDs = nº de clientes | `REFUTED` | R-03 N:1; spec `drm-shared` "more than a single handle" |
| 4 | ausencia de PASID = ausencia de atribución | `REFUTED` | R-15 condicional; relación distinta |
| 5 | un nombre creado por el agente prueba semántica de kernel | `REFUTED` | `AGENTS.md:40-48`; el nombre es `AGENT_FORMALIZATION` |
| 6 | reutilizar un veredicto cuyo basis cambió | `PROHIBIDO` | `AGENTS.md:277-280` |
| 7 | convertir `SOURCE_INCOMPLETE` en FAIL | `PROHIBIDO` | §9 |
| 8 | `card_clients` cuenta clientes | `REFUTED` / `NAME_NOT_EVIDENCE` | contaba FDs |
| 9 | `drm-client-id` es "inmutable" | `REFUTED` sin alcance | una escritura en el core, campo **público**, spec no promete estabilidad |
| 10 | el harness estaba anclado por número de línea | `REFUTED` (mi clasificación) | `_assignment(MAIN, "root_coverage")` es estructural; el guard `PRODUCER_FREE_NAMES` hizo su trabajo |
| 11 | `scan_fds → fdinfo_attribution` era el camino sin cubrir | `REFUTED` (mi premisa) | `scan_fds` acumula con `fdinfo_field_present`; `fdinfo_attribution` **no tiene llamadas** |

## 9 · UNKNOWN · SOURCE_INCOMPLETE · CONFLICTS

| | `CLASS` |
|---|---|
| clave de deduplicación de `drm-client-id` (`C-4`) | `CONFLICT_UNRESOLVED` |
| page-fault `client-id` = `drm-client-id` (`C-1`) | `CONFLICT_UNRESOLVED` |
| sentidos de "client" (`C-2`) | `CONFLICT_UNRESOLVED` |
| `VM`, `PASID`↔`drm_file`, `driver_priv` amdgpu, R-14, R-16, E-15, E-17 | `SOURCE_INCOMPLETE` |
| `engine`/`memory` en este host | `NOT_OBSERVED` (la spec **sí** está disponible) |
| `drm_client_id` **distintos** | `REQUIERE_DEFINICIÓN`: falta el **valor** |

## 10 · Falsificadores

| Afirmación | Falsificador | `STATUS` |
|---|---|---|
| R-02 1:1 | un `struct file` con dos `drm_file` | `AVAILABLE` |
| R-03 N:1 | dos FDs del mismo `drm_file` con `client_id` distinto | `AVAILABLE` |
| R-04 1:1 | dos `drm_file` con el mismo `client_id` | `AVAILABLE` |
| unicidad global | implementación por dispositivo con `client-id` repetido y `drm-pdev` presente | `AVAILABLE` (resolvería `C-4`) |
| R-08 mutable | `drm_file_update_pid` inoperante | `AVAILABLE` |
| R-08 excepción master | un master cuyo pid siga al usuario actual | `AVAILABLE` |
| E-5 constante | dos `drm_file` del mismo dispositivo con `drm-pdev` distinto | `AVAILABLE` |
| R-10 transferible | un master transferido sin `lessor` | `AVAILABLE` |
| R-15 condicional | `PASID` impreso con PID sin fault concurrente | `AVAILABLE` |
| R-12/R-13 por cliente | clave de esas familias por proceso en la spec | `AVAILABLE` |
| `engine=0` no prueba no-uso | spec que definiera `0` como "sin trabajo" | `AVAILABLE` |
| R-11 `driver_priv` | — | `NOT_AVAILABLE` |
| R-14/R-16 | — | `NOT_AVAILABLE` (`SOURCE_INCOMPLETE`) |

**Verificados por ejecucion**: 4 mutaciones del consumidor (cláusula cruzada, `pasid`→`max()`,
`STATE` exige presencia, acumulación de `scan_fds` colapsada) **detectadas**; y una premises mía
refutada por no detección. `test_node_field_presence.py` 14/14 · suite **308 OK**.

## 11 · Separación técnica ↔ proyecto

`PROJECT_MAPPING` = **`NOT_ATTEMPTED`**. El modelo **no** decide qué exige `OWNERSHIP=FULL`, qué
significa "complete attributable evidence", ni qué predicado debe usar el proyecto. Ninguna
propiedad de este documento se presenta como requisito del proyecto.
