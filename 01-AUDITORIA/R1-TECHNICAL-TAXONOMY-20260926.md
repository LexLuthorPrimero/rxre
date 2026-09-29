# R1-TECHNICAL-TAXONOMY-20260926

`DOCUMENT_KIND` = `TECHNICAL_TAXONOMY` · **READ_ONLY** · solo documentación
`HUMAN_REQUIREMENT_STATUS` = `MIXED/AMBIGUOUS_REQUIREMENT_CORRECTED_BY_DECOMPOSITION`
`HUMAN_MIXED_TERM` = `RETIRED_AS_SINGLE_PROPERTY` · `PROJECT_MAPPING` = `NOT_ATTEMPTED`
`PASS_FAIL` = `NOT_DEFINED` · `ANY_ALL` = `NOT_DECIDED` · `TECHNICAL_MODEL` = `CLOSED` (sin modificar)
Sin cambios en código, tests, `AGENTS.md`, `README.md` ni sistema. Sin commit.

## 0 · QUÉ ES Y QUÉ NO ES ESTE DOCUMENTO

Es una **taxonomía técnica**: separa conceptos y fija su semántica de kernel. **No** decide cómo se
implementa `OWNERSHIP`, ni activa ninguna propiedad, ni convierte nada en requisito.

Estructura conservada — **dos árboles, no uno**:

```
HUMAN_REQUIREMENT  (MIXED -> corregido por descomposicion)
  |
  +-- FD_UNIVERSE_COVERAGE        base EXPLICIT
  +-- DRM_NODE_PCI_IDENTITY       base EXPLICIT
  +-- OWNERSHIP_VERDICT           base EXPLICIT  -> CLASS = PROJECT_VERDICT
  |                                          NO es propiedad del kernel
  |
TECHNICAL_PROPERTY  (todo lo que surgio en la formalizacion)
  |
  +-- definicion independiente
  +-- PROVENANCE = AGENT_FORMALIZATION | KERNEL_SOURCE | INFERENCE
  +-- NORMATIVE_STATUS = PROPOSED_NOT_ACTIVE | RETIRED
  +-- NO atribuido al humano salvo evidencia explicita
```

## 1 · ÁRBOL HUMANO — 3 elementos

| | `NAME` | `HUMAN_BASIS` | Cita literal | `CLASS` | `NORMATIVE_STATUS` |
|---|---|---|---|---|---|
| H-1 | `FD_UNIVERSE_COVERAGE` | **`EXPLICIT`** | «complete», «FD visibility is incomplete», «root namespaces are not covered», «a permission is denied» | `TECHNICAL_PROPERTY` | pendiente de decisión humana |
| H-2 | `DRM_NODE_PCI_IDENTITY` | **`EXPLICIT`** | «identified by PCI identity rather than by node name» | `TECHNICAL_PROPERTY` | pendiente de decisión humana |
| H-3 | `OWNERSHIP_VERDICT` | **`EXPLICIT`** | `OWNERSHIP != FULL` / `FULL` | **`PROJECT_VERDICT`** | **`REQUIREMENT_DEFECTIVE`**: el veredicto es humano, su **criterio** usa el término retirado |

**Nada más pertenece al árbol humano.** En particular, H-3 **no es una propiedad del kernel**: es el
consumidor final. Su `TARGET` es el proyecto, su `SOURCE` es `AGENTS.md:170-183`, y su
`ENTITY` no existe en el kernel.

## 2 · ÁRBOL TÉCNICO — 11 elementos, ninguno normativo

Campos conservados por elemento. `SEMANTICS` describe lo que el kernel establece; **no** se cierra
la decisión de si el proyecto lo exige.

| | `NAME` | `ENTITY` / `UNIT` | `SOURCE` | `LIFETIME`/`MUTABILITY` | `OBSERVABILITY` | `LIMITATIONS` | `FALSIFIER` | `PROVENANCE` | `NORMATIVE_STATUS` |
|---|---|---|---|---|---|---|---|---|---|
| T-1 | `DRM_NODE_EXISTENCE` | `drm_minor` / nodo | sysfs `class/drm/` | del minor / cambia si el driver reenumera | `EXPOSED` | `cardN` no es identidad entre hosts | symlink a nodo ausente, roto o de otro BDF | `AGENT_FORMALIZATION` | `PROPOSED_NOT_ACTIVE` |
| T-2 | `DRM_CLIENT_IDENTITY` | `struct drm_file` / un `drm_file` | `drm_file.c:142,942-943`; spec `:64-72` | `open()`→`close()` / inmutable en el core | `PRESENCE` por fdinfo; **`VALUE` no implementada** | unicidad global **o** por dispositivo (`C-4`); contador `static` de módulo (`:132`) | dos `drm_file` con el mismo `client_id` en el dominio de unicidad | `AGENT_FORMALIZATION` + `KERNEL_SOURCE` | `PROPOSED_NOT_ACTIVE` |
| T-3 | `DRM_CLIENT_PROCESS_ASSOCIATION` | `drm_file.pid` / relación | `drm_file.c:143`; `drm_file.h:271-278`; `drm_debugfs.c:92,98-103` | por instancia / **mutable**, documentado (`drm_file.h:275-277`) | `EXPOSED` por debugfs; **no** por fdinfo | dirección **opuesta** a `FD_UNIVERSE_COVERAGE`; sitio de reasignación `SOURCE_NOT_LOCATED` | `drm_clients_info` sin columna `tgid`; o `:272` describiendo al proceso original | `AGENT_FORMALIZATION` + `KERNEL_SOURCE` | `PROPOSED_NOT_ACTIVE` |
| T-4 | `DRM_CLIENT_TO_DEVICE_ASSOCIATION` | `drm_file`→minor→device→PCI / relación | `drm-pdev`; `drm_file.minor` | la del file / inmutable | `EXPOSED` condicional (`dev_is_pci`) | solo existe contador `pooled`, no relación por file | dos `drm_file` del mismo dispositivo con `drm-pdev` distinto | `AGENT_FORMALIZATION` + `KERNEL_SOURCE` | `PROPOSED_NOT_ACTIVE` |
| T-5 | `AMDGPU_VM_PROCESS_CONTEXT` | VM / PASID / proceso / vmid | — | `UNKNOWN` / `UNKNOWN` | `NOT_ESTABLISHED` | **`SOURCE_INCOMPLETE`**; sin falsador disponible → `PROVISIONAL` | `pasid` junto a PID sin fault concurrente | `INFERENCE` (núcleo ausente) | `PROPOSED_NOT_ACTIVE` |
| T-6 | `DRM_CLIENT_MEMORY_ACCOUNTING` | `drm_file` / agregado por file y región | `drm_file.c:828-840`; spec `:140-175` | derivada de `object_idr` / derivada | por driver; `NOT_OBSERVED` | `=0` no prueba no-uso; no es inventario | clave de memoria indexada por proceso en la spec | `AGENT_FORMALIZATION` + `KERNEL_SOURCE` | `PROPOSED_NOT_ACTIVE` |
| T-7 | `DRM_CLIENT_ENGINE_ACTIVITY` | `drm_file`×engine / ns acumuladas | spec `:79-137` (`:86`, `:88-89`) | contador del driver / **no monótona** | por driver; `NOT_OBSERVED` | no es estado instantáneo; `=0` no prueba no-uso | `drm-engine-*` por proceso, o declarada monótona | `AGENT_FORMALIZATION` + `KERNEL_SOURCE` | `PROPOSED_NOT_ACTIVE` |
| T-8 | `DRM_MASTER_RELATION` | `drm_master` / un master | `drm_lease.h`; `drm_auth.c:81` | `kref` / **transferible** | por ioctl, no por fdinfo | `NOT_APPLICABLE` en nodos no primarios | master transferido sin `lessor` | `AGENT_FORMALIZATION` + `KERNEL_SOURCE` | `PROPOSED_NOT_ACTIVE` |
| T-9 | `GEM_OBJECT_RELATION` | `drm_gem_object` / un objeto | `drm_file.h:299-304`; `drm_gem.h` | la del objeto / `object_idr` mutable | **no observable** desde espacio de usuario | un GEM es alcanzable desde varios `drm_file`; no es identidad de proceso | fuente que haga del GEM identidad de proceso | `AGENT_FORMALIZATION` + `KERNEL_SOURCE` | `PROPOSED_NOT_ACTIVE` |
| T-10 | `drm_client_dev` | **no establecida** / nodo de apertura | **sin fuente primaria**: solo existe `drm_client_dev_restore(dev)` (`drm_file.c:391`), llamado desde `drm_lastclose()`; **definición `SOURCE_NOT_LOCATED`** | `UNKNOWN` / `UNKNOWN` | `NOT_ESTABLISHED` | el nombre aparece en el texto del proyecto, **no** en el kernel como entidad | un símbolo `drm_client_dev` con esa semántica en v6.12 | `AGENT_FORMALIZATION` (el nombre) · `UNKNOWN` (la semántica) | `PROPOSED_NOT_ACTIVE` |
| T-11 | `DRM_CLIENT_DEDUPLICATION` | conjunto de aperturas / `distinct drm-client-id` | clave derivada de `drm-client-id` | re-evaluable | requiere `VALUE` | depende de `C-4` | dos `drm_file` con la misma clave | `AGENT_FORMALIZATION` | **`RETIRED`** — su única base era la interpretación retirada («12 clientes») |

**Nota sobre T-10**: se conserva porque el texto del proyecto lo nombra y separar exige no borrarlo en
silencio; queda explícitamente **sin fuente primaria** y con `PROVENANCE` declarada. No se le
atribuye semántica.

## 3 · ENTIDADES QUE NO SON PROPIEDADES

Se conservan separadas, con su nombre de kernel, y **sin** ser propiedades de este modelo:

`FD` · `struct file` · `struct drm_file` · `drm-client-id` · `drm-pdev` · `drm_minor` (4 tipos ABI:
`PRIMARY=0`, `CONTROL=1`, `RENDER=2`, `ACCEL=32`; `drm_file.h:61-66`) · `drm_device` ·
`PID/TGID` · `drm_master` · `GEM object` · `memory statistics` · `engine statistics` · `VM` ·
`PASID` · GPU page-fault `client-id` · fila del fichero debugfs `clients` (**1 fila = 1
`drm_file`**, `drm_debugfs.c:92,143`).

**«client» no se usa como nombre genérico.** El kernel nombra «client» a **cinco** entidades:
`drm_file` · `debugfs_client_entry` · `drm_master` · `gpu_page_fault_client_id` ·
`accel_minor_file` (`drm_is_accel_client`, `drm_file.h:432`). Aquí «cliente» solo significa
`struct drm_file`, y esa atribución es lo que elimina la ambigüedad.

## 4 · FILAS DE CRITERIO SIN PROPIEDENCIA

`writers_resolved` y `guard_and_restore` existen como filas en `OWNERSHIP_CRITERION_ROWS` y **no**
tienen ficha. La primera tiene base textual humana («a writer is unresolved») pero **sin definición
técnica**: es una laguna de la formalización del agente, no un requisito humano sin propiedad.
`CLASS = CRITERION_ROW_WITHOUT_PROPERTY`. **No se pide decisión humana sobre ellas.**

## 5 · COMPROBACIÓN FINAL

| Verificación | Resultado |
|---|---|
| ¿Algún `PROJECT_VERDICT` presentado como requisito humano? | **NO** — H-3 lleva `CLASS = PROJECT_VERDICT` y `REQUIREMENT_DEFECTIVE` |
| ¿Algún `PROPOSED_NOT_ACTIVE` presentado como requisito humano? | **NO** — los 10 llevan `PROVENANCE = AGENT_FORMALIZATION` (± `KERNEL_SOURCE`/`INFERENCE`) y `NORMATIVE_STATUS` explícito |
| ¿Algún elemento del árbol técnico con base humana? | **NO** — H-1 y H-2 son las únicas con cita literal; ninguna de las 11 aparece en el texto humano |
| ¿Se reabrió la investigación de `attributable`? | **NO** — el término está `RETIRED_AS_SINGLE_PROPERTY` y no se usa como predicado |
| ¿Se cerró prematuramente la semántica técnica? | **NO** — T-5 y T-10 siguen `SOURCE_INCOMPLETE`/`NOT_ESTABLISHED`; el resto tiene `SEMANTICS` de kernel y `NORMATIVE_STATUS` abierto |
| ¿Se usan «client», `any()`, `all()`, `PASS`/`FAIL` como agregadores? | **NO** — `ANY_ALL = NOT_DECIDED`, `PASS_FAIL = NOT_DEFINED` |

## 6 · ESTADO

```
HUMAN_REQUIREMENT_TREE   = 3 elementos (2 propiedades técnicas + 1 PROJECT_VERDICT)
TECHNICAL_PROPERTY_TREE  = 11 elementos (10 PROPOSED_NOT_ACTIVE + 1 RETIRED)
CRITERION_ROWS_WITHOUT_PROPERTY = 2
PROJECT_MAPPING          = NOT_ATTEMPTED
PASS_FAIL                = NOT_DEFINED
ANY_ALL                  = NOT_DECIDED
TECHNICAL_MODEL          = CLOSED (sin modificar)
CODE_CHANGES             = NONE
```

La taxonomía está separada. **No se decide nada normativo**: la siguiente decisión sigue siendo
escribir el criterio de `OWNERSHIP` en términos de H-1 y H-2, o declarar que ninguno de los dos
basta.
