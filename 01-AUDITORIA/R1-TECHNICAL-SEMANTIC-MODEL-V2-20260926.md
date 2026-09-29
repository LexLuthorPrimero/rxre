# R1-TECHNICAL-SEMANTIC-MODEL-V2-20260926

`DOCUMENT_KIND` = `TECHNICAL_MODEL` · **READ_ONLY** · consolida, no re-deriva
`TECHNICAL_MODEL_STATUS` = `CLOSED` · `PROJECT_MAPPING` = `NOT_ATTEMPTED` · `PASS_FAIL` = `NOT_DEFINED`
`ANY_ALL` = `NOT_DECIDED` · `HUMAN_MIXED_TERM` = `RETIRED / NO_INTERPRETAR`
`REQUIREMENT_INTENT_RECONSTRUCTION` = `NOT_ATTEMPTED`
Fuentes primarias: linux **v6.12** (`drm_file.c/h`, `drm_debugfs.c`, `drm_drv.h`, `drm_auth.c/h`,
`drm_gem.c/h`, `drm_lease.c/h`, `drm_internal.h`, `drm-usage-stats.rst`). Implementación:
`privileged_read_collector.py` sha `458c9261f61b412c`.
Precede a: `R1-TECHNICAL-MODEL-CLOSURE` `ee86a3a7`, `R1-SEMANTIC-DECOMPOSITION` `0801b7d9`,
`R1-TECHNICAL-SEPARATION-TABLE` `116f011e`, `R1-UNMIXED-TECHNICAL-MODEL` `c1f803a6`.

## A · PROPÓSITO Y ALCANCE

Un modelo de semántica **del kernel**, utilizable para diseñar el proyecto sin volver a mezclar
conceptos. No decide requisitos. No reinterpreta texto humano. No implementa.

## B · CORRECCIÓN DEL ERROR CONCEPTUAL ANTERIOR

El requisito humano usó «evidencia completa, atribuible» como **una** propiedad. Error: la palabra
no tiene unidad. Mezcló **cuatro fuentes** (`/proc/<pid>/fd`, `/proc/<pid>/fdinfo`, sysfs, debugfs)
y **ocho unidades** (FD, apertura DRM, dispositivo, vmid, bloque de motor, proceso, bytes,
nanoseconds). La corrección es **descomponer**, no interpretar.

## C · ENTIDADES (15, cada una con su fuente)

| Entidad | Unidad | Fuente primaria | Observabilidad |
|---|---|---|---|
| `FD` | descriptor | `/proc/<pid>/fd/<n>` | `EXPOSED` |
| `struct file` | un `struct file` | `private_data` (`drm_show_fdinfo`) | **no expuesto** |
| `struct drm_file` | **una apertura DRM** | `drm_file.h:164-391` | no expuesto; sí resumible |
| `drm-client-id` | `u64`, 1:1 con `drm_file` | `drm_file.c:942-943`; spec `:64-72` | `EXPOSED` |
| `drm-pdev` | BDF del dispositivo | `drm_file.c:948-950`; spec `:59-62` | `EXPOSED` sii `dev_is_pci` |
| `drm_minor` | nodo | `drm_file.h:61-86` | `EXPOSED` |
| `drm_minor.type` | **cuatro** valores ABI, `include/drm/drm_file.h:61-66` (linux **v6.12 mainline**, `FACT_FOR_v6.12=VERIFIED`; `APPLICABILITY_TO_HOST_KERNEL=INFERENCE_UNLESS_VERIFIED` para el 7.1.3 del host): `PRIMARY=0` (cardN), `CONTROL=1` (controlDN), `RENDER=2` (renderDN), **`ACCEL=32`** (accel*) — el `32` es espacio reservado deliberado (`drm_file.h:58`). **CORREGIDO**: la revisión anterior de esta fila decía `ACCEL=3`, un `FACT` falso; el número de línea era correcto, el valor no. El tipo se consulta con los predicados `drm_file_is_primary`/`drm_file_is_render`/`drm_file_is_accel` (`drm_file.h:405,419,434`), no con literales |
| `drm_device` | driver+dispositivo | `drm_drv.h` | `EXPOSED` |
| PID/TGID | proceso | `drm_file.c:143` = `task_tgid` | `EXPOSED` por debugfs |
| `drm_master` | un master | `drm_lease.h` | por ioctl |
| GEM object | un `drm_gem_object` | `drm_gem.h`; `drm_file.h:299-304` | no observable |
| memoria contabilizada | agregado | spec `:140-175` | por driver |
| engine | `drm_file`×engine | spec `:79-137` | por driver |
| `VM` | — | — | `SOURCE_INCOMPLETE` |
| `PASID` | vmid | — | `SOURCE_INCOMPLETE` |
| page-fault `client-id` | bloque del motor | — | `SOURCE_INCOMPLETE` |

## D–H · PROPIEDADES SEPARADAS (9 fichas, estructura exacta solicitada)

### A · `NODE_VISIBILITY` (antes `NODE_COMPLETENESS`)
`ENTITY`: proceso × nodo DRM · `UNIT`: **`process × DRM node`**
`DEFINITION`: si puede determinarse que la población relevante de procesos fue examinada respecto de los nodos DRM, con la cobertura exigida
`SOURCE`: los cuatro términos de visibilidad del universo de FDs por nodo
`OBSERVABILITY`: `EXPOSED`; depende del privilegio y del namespace
`IDENTITY_SEMANTICS`: cobertura de un universo; **no** identidad de nada
`LIFETIME`: la del barrido · `MUTABILITY`: re-evaluable
`WHAT_IT_PROVES`: que el universo quedó recorrido, y **dónde** dejó de recorrerse
`WHAT_IT_DOES_NOT_PROVE`: identidad de cliente · asociación con proceso · actividad GPU · que un cliente esté inactivo
`REQUIRED_FIELDS`:Fd enumeration, legibilidad de fdinfo, cobertura de namespaces
`OPTIONAL_FIELDS`: ninguno
`KNOWN_LIMITATIONS`: cobertura parcial ≠ completa; no cubre el minor `ACCEL` (`drm_file.h:65`)
`KNOWN_CONFLICTS`: ninguna
`FALSIFIER`: mismo universo y privilegio con los 4 términos satisfechos y una fila de FDs ausente
`CLASSIFICATION`: `ESTABLISHED`

### B · `NODE_PROCESS_ASSOCIATION`
`ENTITY`: proceso → FD → nodo · `UNIT`: **`process → FD → DRM node`**
`DEFINITION`: que un FD observado pertenece a un proceso concreto **y** referencia un nodo DRM concreto
`SOURCE`: `/proc/<pid>/fd/<n>` (symlink) + `/proc/<pid>/fdinfo/<n>`; error de lectura conservado (`read_bytes`+`status`)
`OBSERVABILITY`: `EXPOSED`; protegido por guard que prohíbe `read_text` (degrada a `""`)
`IDENTITY_SEMANTICS`: **dos** hechos encadenados: posesión del descriptor y resolución del destino. Ninguno implica `client_id`
`LIFETIME`: la del FD · `MUTABILITY`: re-evaluable
`WHAT_IT_PROVES`: qué proceso poseía ese descriptor y a qué nodo apuntaba
`WHAT_IT_DOES_NOT_PROVE`: que el FD sea un `drm_file`; identidad de cliente; actividad
`REQUIRED_FIELDS`: symlink destino, pid, legibilidad
`OPTIONAL_FIELDS`: cmdline, uid, namespaces
`KNOWN_LIMITATIONS`: `NOT_OBSERVED` ≠ el proceso no tenía el FD
`KNOWN_CONFLICTS`: ninguna
`FALSIFIER`: `/proc/<pid>/fd/<n>` resuelriendo a otro nodo; o `read_text` en la ruta de fdinfo (ejecutado: detectado)
`CLASSIFICATION`: `ESTABLISHED`

### C · `DRM_FILE_IDENTITY`
`ENTITY`: `struct drm_file` · `UNIT`: **`drm_file` / `drm-client-id`**
`DEFINITION`: identificar el `struct drm_file` mediante `drm-client-id`; conceptualmente 1:1 (spec `:66-68`)
`SOURCE`: `drm_file.c:142` (una sola escritura), `:942-943`; campo `drm_file.h:281-282`
`OBSERVABILITY`: `PRESENCE` por fdinfo; **`VALUE` no preservada en el proyecto**
`IDENTITY_SEMANTICS`: `drm-client-id` identifica la **apertura**, no el FD ni el proceso. Varios FD pueden referenciar la misma apertura (`dup()`/`fork()`)
`LIFETIME`: `open()`→`close()`; `dup()`/`fork()` **no** crean `drm_file`
`MUTABILITY`: inmutable en el core; el campo es **público** y la spec no promete estabilidad
`WHAT_IT_PROVES`: que el texto traía la clave; y, con valor, la identidad de la apertura
`WHAT_IT_DOES_NOT_PROVE`: `client_id` = PID · FD · proceso · `drm_master` · PASID · page-fault `client-id`; ni el nº de clientes
`REQUIRED_FIELDS`: presencia de `drm-client-id`; para valor: el literal
`OPTIONAL_FIELDS`: `drm-pdev` (necesario si la unicidad es por dispositivo)
`KNOWN_LIMITATIONS`: contador `static` de módulo (`drm_file.c:132`) → unicidad dentro de la vida del módulo `drm`
`KNOWN_CONFLICTS`: `C-4` (unicidad global o por dispositivo) `CONFLICT_UNRESOLVED`
`FALSIFIER`: dos `drm_file` distintos con el mismo `client_id` **dentro del dominio donde la spec exige unicidad**. **No** es falsificador «el campo no apareció»: causas alternativas son clave opcional, driver que no exporta, fdinfo no leído, acceso denegado, proceso desaparecido, parser defectuoso
`CLASSIFICATION`: `PARTIALLY_ESTABLISHED` (semántica `ESTABLISHED`; `VALUE` = `NOT_AVAILABLE`)

### D · `PCI_DEVICE_IDENTITY`
`ENTITY`: DRM device / PCI device · `UNIT`: **dispositivo**
`DEFINITION`: identificar inequívocamente el dispositivo PCI al que pertenece el `drm_file`
`SOURCE`: `drm-pdev` (`drm_file.c:948-950`, solo sii `dev_is_pci`); spec `:59-62`; sysfs `minor->dev`
`OBSERVABILITY`: `EXPOSED`; ausente en dispositivos no-PCI
`IDENTITY_SEMANTICS`: **dirección PCI del dispositivo**, constante por dispositivo. **Todos** los clientes de ese dispositivo comparten el mismo valor → no identifica cliente
`LIFETIME`: la del dispositivo · `MUTABILITY`: inmutable
`WHAT_IT_PROVES`: a qué dispositivo pertenece una apertura
`WHAT_IT_DOES_NOT_PROVE`: identidad de cliente; nº de clientes; unicidad de nada mas
`REQUIRED_FIELDS`: `drm-pdev` o BDF por sysfs
`OPTIONAL_FIELDS`: vendor, device, class, driver
`KNOWN_LIMITATIONS`: `drm-pdev` no transporta vendor/device/class
`KNOWN_CONFLICTS`: ninguna
`FALSIFIER`: `drm-pdev` emitiendo algo que no sea `domain:bus:slot.func`; o dos `drm_file` del mismo dispositivo con `drm-pdev` distinto
`CLASSIFICATION`: `ESTABLISHED`

### E · `PROCESS_TO_DRM_CLIENT_ASSOCIATION`
`ENTITY`: proceso ↔ `drm_file`/`drm-client-id` · `UNIT`: **`process → drm_file/client-id`**
`DEFINITION`: relacionar un proceso observado con uno o más `drm_file` observados
`SOURCE`: dirección 1 `drm_file.pid` (`drm_file.c:143`; `drm_file.h:271-278` «Process that is **using** this file»), expuesta por el core en `debugfs/dri/<minor>/clients` columna `tgid` (`drm_debugfs.c:92,98-103,143`). Dirección 2: `FD → struct file → drm_file` (`private_data`)
`OBSERVABILITY`: dirección 1 **no** por fdinfo, **sí** por debugfs (fila por `drm_file`); dirección 2 por `/proc`
`IDENTITY_SEMANTICS`: **dirección opuesta** a B. B responde «qué proceso **posee** este FD»; E responde «qué proceso **usa** esta apertura». No son la misma relación
`LIFETIME`: por instancia; el `pid` **no** es la identidad histórica del opener
`MUTABILITY`: **mutable**, documentado en la fuente (`drm_file.h:275-277`); updater `drm_file.c:435`; sitio de llamada `SOURCE_NOT_LOCATED`; `drm_auth.c:236-238` lo compara con `task_tgid(current)`
`WHAT_IT_PROVES`: que hay una asociación observable entre una apertura y un TGID
`WHAT_IT_DOES_NOT_PROVE`: `PID == client_id` · `FD == client_id` · `process == drm_file`; ni que ese proceso sea el que abrió el FD
`REQUIRED_FIELDS`: para la dirección 1, la fila de debugfs; para la 2, el symlink del FD
`OPTIONAL_FIELDS`: `master` (y/n), `uid`, `magic` de la misma fila
`KNOWN_LIMITATIONS`: el carrier debugfs **no** fue preservado por el proyecto; la fila no contiene `drm-client-id` (`magic` es `drm_magic_t`, `drm_file.h:285`)
`KNOWN_CONFLICTS`: ninguna
`FALSIFIER`: `drm_clients_info` sin columna `tgid`; o `drm_file.h:272` describiendo al proceso **original**; o `drm_file_update_pid` inoperante
`CLASSIFICATION`: `ESTABLISHED` (semántica) · `NOT_IMPLEMENTED` (dirección 1)

### F · `DRM_CLIENT_DEDUPLICATION`
`ENTITY`: conjunto de aperturas · `UNIT`: **`distinct drm-client-id`**
`DEFINITION`: contar clientes DRM distintos sin confundir FD duplicado, múltiples FDs, múltiples `drm_file`, múltiples procesos y `drm-client-id`
`SOURCE`: clave derivada de `drm-client-id` (spec `:64-72`)
`OBSERVABILITY`: requiere **`VALUE`**, no `PRESENCE`; hoy `NOT_AVAILABLE`
`IDENTITY_SEMANTICS`: la clave de deduplicación es `drm-client-id` si la unicidad es **global**, y **`(drm-pdev, drm-client-id)`** si es **por dispositivo** — porque en ese modelo dos dispositivos pueden repetir el mismo `client-id`, y `drm-pdev` es lo que los desambigua (spec `:70-71`). `drm-pdev` **por sí solo no** identifica un cliente: es constante por dispositivo
`LIFETIME`: la del conjunto de aperturas · `MUTABILITY`: re-evaluable
`WHAT_IT_PROVES`: cuántas aperturas DRM distintas hubo
`WHAT_IT_DOES_NOT_PROVE`: **nunca** `#FD` · **nunca** `#procesos`; ni identifica *qué* hace cada una
`REQUIRED_FIELDS`: los valores literales de `drm-client-id` (+ `drm-pdev` si la unicidad es por dispositivo)
`OPTIONAL_FIELDS`: TGID para agrupar por proceso (agregación distinta, no identidad)
`KNOWN_LIMITATIONS`: `#FD` es un **techo** de `#drm_file`, no su equivalente; con `dup()`/`fork()` la diferencia es real y observada
`KNOWN_CONFLICTS`: `C-4` `CONFLICT_UNRESOLVED` — la clave depende de una decisión sobre unicidad que la spec deja abierta
`FALSIFIER`: dos `drm_file` con el mismo `drm-client-id` bajo la misma clave; o, en el modelo por dispositivo, el mismo `client-id` en dos dispositivos con `drm-pdev` distinto **sin** ser error
`CLASSIFICATION`: `NOT_ESTABLISHED` (falta `VALUE` y resolver `C-4`)

### G · `MEMORY_ACCOUNTING_ATTRIBUTION`
`ENTITY`: `drm_file` · `UNIT`: **agregado por `drm_file` y región**
`DEFINITION`: qué estadísticas de memoria pertenecen a ese `drm_file`/cliente
`SOURCE`: `drm_print_memory_stats` (`drm_file.c:828-840`); spec `:140-175` — `drm-memory-<region>` (`:143`), `drm-shared-` (`:155`), `drm-total-` (`:160`), `drm-resident-` (`:164`), `drm-purgeable-` (`:168`), `drm-active-` (`:172`)
`OBSERVABILITY`: por driver; el core emite las claves, el driver las rellena
`IDENTITY_SEMANTICS`: estadística **del cliente**, con sus buffer objects. No es contabilidad por PID
`LIFETIME`: derivada de `object_idr` · `MUTABILITY`: derivada
`WHAT_IT_PROVES`: consumo agregado de esa apertura por región
`WHAT_IT_DOES_NOT_PROVE`: **memoria del proceso**; inventario de objetos; `=0` como prueba de no-uso
`REQUIRED_FIELDS`: las claves `drm-<stat>-<region>` de ese file
`OPTIONAL_FIELDS`: región, unidades (`KiB`/`MiB`)
`KNOWN_LIMITATIONS`: `=0` **no** prueba no-uso; `NOT_OBSERVED` en este host
`KNOWN_CONFLICTS`: ninguna
`FALSIFIER`: clave de memoria indexada por proceso en la spec
`CLASSIFICATION`: `ESTABLISHED` (semántica) · `NOT_OBSERVED` (host) · `NOT_IMPLEMENTED` (proyecto)

### H · `ENGINE_ACTIVITY_ATTRIBUTION`
`ENTITY`: `drm_file`/cliente × engine · `UNIT`: **ns acumuladas por engine**
`DEFINITION`: qué actividad de engine puede establecerse para ese cliente
`SOURCE`: spec `:79-137`; `:86` «time the engine spent busy executing workloads belonging to **this client**»; `:88-89` **no monótona**
`OBSERVABILITY`: por driver · `IDENTITY_SEMANTICS`: tiempo **acumulado** del engine por cliente
`LIFETIME`: contador del driver · `MUTABILITY`: **no monótona** → ante retroceso, retener el máximo
`WHAT_IT_PROVES`: trabajo acumulado de esa apertura
`WHAT_IT_DOES_NOT_PROVE`: `engine → PID`; `engine → proceso` sin relación adicional demostrada; estado instantáneo; `=0` como prueba de no-uso
`REQUIRED_FIELDS`: `drm-engine-<keystr>` de ese file
`OPTIONAL_FIELDS`: `keystr` (engine), `drm-total-cycles-`, frecuencia máxima
`KNOWN_LIMITATIONS`: `NOT_OBSERVED` en este host; no implementada
`KNOWN_CONFLICTS`: ninguna
`FALSIFIER`: `drm-engine-*` indexada por proceso, o declarada monótona
`CLASSIFICATION`: `ESTABLISHED` (semántica) · `NOT_OBSERVED` · `NOT_IMPLEMENTED`

### I · `VM_PASID_PROCESS_RELATION`
`ENTITY`: VM / PASID / proceso · `UNIT`: **vmid**
`DEFINITION`: qué relación puede establecerse entre VM, PASID y proceso
`SOURCE`: **`SOURCE_INCOMPLETE`** — 0 ocurrencias de `pasid` en `drm-usage-stats.rst`; 0 en el core v6.12; docs de amdgpu inaccesibles (404 en 3 mecanismos)
`OBSERVABILITY`: `NOT_ESTABLISHED`
`IDENTITY_SEMANTICS`: PASID = **vmid**. **NO** es `drm-client-id`, **NO** es PID, **NO** es `drm_file`, **NO** es «cliente DRM»
`LIFETIME`: la del VM · `MUTABILITY`: `UNKNOWN`
`WHAT_IT_PROVES`: nada en este host
`WHAT_IT_DOES_NOT_PROVE`: identidad permanente de proceso; identidad DRM; cualquier equated con `client_id`
`REQUIRED_FIELDS`: fuente primaria de amdgpu
`OPTIONAL_FIELDS`: —
`KNOWN_LIMITATIONS`: la relación VM↔PASID↔proceso sería **episódica** (durante un page fault y con el proceso activo) según documentación no obtenida → **no se afirma**
`KNOWN_CONFLICTS`: `C-1` page-fault `client-id` = `drm-client-id` `CONFLICT_UNRESOLVED`
`FALSIFIER`: `pasid` impreso junto a un PID sin fault concurrente. **No disponible** con las fuentes actuales → la ficha queda `PROVISIONAL`
`CLASSIFICATION`: `SOURCE_INCOMPLETE`

## E · RELACIONES (dirección y unidad)

| Relación | Dirección | Unidad | Cardinalidad | Condición |
|---|---|---|---|---|
| R-01 | `FD → struct file` | descriptor | **N:1** | `dup()`/`fork()` |
| R-02 | `struct file → drm_file` | — | **1:1** | `private_data` |
| R-03 | `FD ↔ drm_file` | — | **N:1** | vía R-01/R-02 |
| R-04 | `drm_file → client_id` | — | **1:1** | una escritura |
| R-05 | `drm_file → pid` | — | 1:1 actual | **mutable** |
| R-06 | `drm_file → minor → drm_device → PCI` | — | N:1 · 1:1 | `dev_is_pci` para `drm-pdev` |
| R-06b | `drm_file.minor → minor.type` (primary/render/control/accel) | `drm_file` | N:1 | determina a qué **clase de nodo** pertenece la apertura; `drm_is_accel_client()` (`:432`) decide por `minor->type`. Un mismo `drm_device` expone **varios** minors, así que «el nodo de esta apertura» **no** es único sin `type` |
| R-07 | `drm_file → object_idr → GEM` | — | 1:N | `table_lock` |
| R-08 | `drm_file ↔ drm_master` | — | 1:0:1 | nodo primario; **transferible** |
| R-09 | `dev → filelist → drm_file` | — | 1:N | base de la fila debugfs |
| R-10 | `VM ↔ PASID` | — | `UNKNOWN` | `SOURCE_INCOMPLETE` |

## F · UNIDADES — cuatro cantidades que NO son intercambiables

| Cantidad | Unidad | Qué la origina |
|---|---|---|
| número de FDs | **FD** | `/proc/<pid>/fd` |
| número de `drm_file` | **apertura DRM** | R-01/R-02: **≤** nº de FDs, estrictamente menor con `dup()`/`fork()` |
| número de `drm-client-id` distintos | **`drm_file`** | R-04 + unicidad |
| número de procesos | **proceso** | varios procesos pueden compartir un `drm_file` (leasing, herencia) |

`#FD ≥ #drm_file` y `#drm_file ≠ #procesos`. Ninguna se deriva de otra por aritmética.

## G · LIFECYCLE / MUTABILIDAD

`drm_file`: `open()`→`close()`, inmutable salvo `pid` (documentado en la fuente).
`client_id`: inmutable en el core; **público**; único dentro de la vida del módulo `drm`.
`drm-pdev`: inmutable, constante por dispositivo. `drm_master`: transferible. `object_idr`: mutable.
`engine`: no monotono. `FD`: re-evaluable.

## H · OBSERVABILIDAD (5 capas, sin colapsar)

| Propiedad | ¿expuesto? | ¿leído? | ¿observado? | ¿demuestra? | ¿satisface requisito? |
|---|---|---|---|---|---|
| `NODE_VISIBILITY` | sí | sí | sí | parcial | `UNKNOWN` |
| `NODE_PROCESS_ASSOCIATION` | sí | sí | sí | sí | `UNKNOWN` |
| `DRM_FILE_IDENTITY` | sí | presencia sí, **valor no** | solo por cita | **no** | `UNKNOWN` |
| `PCI_DEVICE_IDENTITY` | sí | sí | sí (`PROVEN`) | sí | `UNKNOWN` |
| `PROCESS_TO_DRM_CLIENT_ASSOCIATION` | dir.1 sí (debugfs) | no | no | no | `NO` |
| `DRM_CLIENT_DEDUPLICATION` | sí | no | no | no | `NO` |
| `MEMORY_ACCOUNTING_ATTRIBUTION` | por driver | no | no | no | `NO` |
| `ENGINE_ACTIVITY_ATTRIBUTION` | por driver | no | no | no | `NO` |
| `VM_PASID_PROCESS_RELATION` | **no** | no | no | no | `NO` |

## I · EVIDENCIA (4 niveles) — y qué significa ATTRIBUTION en cada relación

`PRESENCE → VALUE → DISCRIMINATION → ATTRIBUTION`. **`ATTRIBUTION` no es una propiedad**: es el
último nivel, y significa algo distinto según la relación.

| Relación | ¿se alcanza `ATTRIBUTION`? | Qué significa **aquí** |
|---|---|---|
| `process → FD → nodo` | **SÍ** (R-01/R-02 + `/proc`) | saber qué proceso posee qué descriptor y a qué nodo apunta |
| `drm_file → client_id` | **NO** | requiere `VALUE`; solo hay `PRESENCE` por cita |
| `drm_file → PCI device` | **NO** | solo existe un contador `drm-pdev` **pooled**, no una relación por file |
| `client → engine activity` | **NO** | no implementado, `NOT_OBSERVED` |
| `client → memoria` | **NO** | ídem |
| `drm_file → TGID` | **NO** por fdinfo; **SÍ** por debugfs (no preservado) | correlación con el proceso que **usa** la apertura |

## J · NO-EQUIVALENCIAS (prohibidas, y refutadas con evidencia)

| Afirmación | Estado | Evidencia |
|---|---|---|
| `FD count = client count` | **REFUTADA** | R-01 N:1; spec `:155-158` «more than a single handle» |
| `PID = drm-client-id` | **REFUTADA** | R-04 vs R-05: campos distintos,Dominios distintos; `drm_file.c:142` vs `:143` |
| `PASID = client identity` | **NO_ESTABLECIDA** | `SOURCE_INCOMPLETE`; no se afirma ni se refuta |
| `PASID = PID` | **NO_ESTABLECIDA** | ídem |
| `drm-pdev = client identity` | **REFUTADA** | `drm-pdev` es BDF, constante por dispositivo (`:948-950`) |
| `GEM object = process` | **REFUTADA** | el idr pertenece al `drm_file` (`drm_file.h:302`); un GEM es alcanzable desde varios `drm_file` |
| `engine stats = process` | **REFUTADA** | spec `:86` «belonging to **this client**», y `:88-89` no monotona |
| `memory stats = process` | **REFUTADA** | spec `:143-155` define por cliente/región; `=0` no prueba no-uso |
| `client-id = page-fault client-id` | **NO_ESTABLECIDA** | `C-1`; fuentes de amdgpu ausentes |
| `process = drm_file` | **REFUTADA** | R-05 es 1:1 *temporal* y mutable; R-08 muestra que un master se transfiere |
| `drm_file = struct file` | **REFUTADA** | R-02 es la unica correspondencia 1:1; R-01 no lo es |

## K · CONFLICTOS TERMINOLÓGICOS

**`CLIENT_TERM_COLLISION = YES`** — cinco entidades distintas nombradas «client» en el propio kernel.
No se resuelven inventando que son la misma:

| # | Entidad | Nombre en el kernel | Nombre propio aquí |
|---|---|---|---|
| 1 | el archivo DRM abierto | `struct drm_file` | `drm_file` |
| 2 | la fila del fichero debugfs | `drm_clients_info` (`:73`), entrada `clients` (`:143`) | `debugfs_client_entry` |
| 3 | el owner de nodos primarios | `drm_master`, `drm_is_current_master` | `drm_master` |
| 4 | el bloque en el informe de page fault | page-fault `client-id` | `gpu_page_fault_client_id` |
| 5 | el archivo sobre un minor de aceleración | `drm_is_accel_client` (`drm_file.h:432`) | `accel_minor_file` |

`DRM_CLIENT_DEBUGFS_FACILITY` conserva el token `CLIENT` **heredado del símbolo**; el nombre no
afirma equivalencia semántica. `drm_client_dev` **no es entidad de kernel**: solo existe
`drm_client_dev_restore(dev)` (`drm_file.c:391`), llamado desde `drm_lastclose()`; su definición
está `SOURCE_NOT_LOCATED`.

## L · FALSIFICADORES

| Propiedad | Falsificador (válido) | `STATUS` |
|---|---|---|
| `NODE_VISIBILITY` | mismo universo y privilegio con los 4 términos y una fila ausente | `AVAILABLE` |
| `NODE_PROCESS_ASSOCIATION` | symlink a otro nodo; o `read_text` en la ruta de fdinfo | `AVAILABLE` (ejecutado) |
| `DRM_FILE_IDENTITY` | dos `drm_file` con el mismo `client_id` en el dominio de unicidad | `AVAILABLE` |
| `DRM_FILE_IDENTITY` unicidad | implementación por dispositivo con `client-id` repetido y `drm-pdev` presente | `AVAILABLE` |
| `PCI_DEVICE_IDENTITY` | `drm-pdev` no-BDF; dos `drm_file` del mismo dispositivo con `drm-pdev` distinto | `AVAILABLE` |
| `PROCESS_TO_DRM_CLIENT_ASSOCIATION` | `drm_clients_info` sin columna `tgid`; `:272` describiendo al proceso original | `AVAILABLE` |
| `DRM_CLIENT_DEDUPLICATION` | dos `drm_file` con la misma clave | `AVAILABLE` |
| `MEMORY_ACCOUNTING_ATTRIBUTION` | clave de memoria por proceso en la spec | `AVAILABLE` |
| `ENGINE_ACTIVITY_ATTRIBUTION` | `drm-engine-*` por proceso, o declarada monótona | `AVAILABLE` |
| `VM_PASID_PROCESS_RELATION` | `pasid` junto a PID sin fault concurrente | `NOT_AVAILABLE` → **`PROVISIONAL`** |

**Falsificadores rechazados por inválidos**: «el campo no apareció», «el conteo no cuadró»,
«el test pasó». Ninguno refuta la afirmación que pretende: todas tienen causas alternativas
documentadas.

## M · LÍMITES DE FUENTE

`SOURCE_INCOMPLETE`: amdgpu (404 en 3 mecanismos) · `drm_client_debugfs.c` sin leer ·
exposición de `object_idr` desde espacio de usuario. `SOURCE_NOT_LOCATED`: sitio de reasignación de
`drm_file.pid` · definición de `drm_client_dev_restore`. `NOT_AVAILABLE`: valor de
`drm-client-id`/`drm-pdev`/`PASID` en todo el repositorio.

## N · ERRORES HISTÓRICOS CORREGIDOS

| Afirmación previa | Estado | Evidencia |
|---|---|---|
| «complete attributable evidence» es una propiedad | **REFUTADA** | 4 fuentes, 8 unidades |
| «1 DRM client» | **REFUTADA** | cobertura ampliada a 12 FDs |
| «12 clientes» | **REFUTADA** | eran 12 FDs en 4 procesos |
| `card_clients` cuenta clientes | **REFUTADA** / `NAME_NOT_EVIDENCE` | contaba FDs |
| `P-9 OBSERVABILITY = NOT_EXPOSED` | **REFUTADA** | `drm_debugfs.c:98-103` publica el TGID |
| `client_id` es «inmutable» sin alcance | **REFUTADA sin alcance** | contador `static` de módulo |
| `drm_client_dev` es entidad de kernel | **PROVENANCE_ERROR** | solo existe `drm_client_dev_restore` |
| `drm-memory-<region>` no existe en la spec | **REFUTADA** (mi hipótesis) | spec `:143` — sí existe |
| `drm_file.pid` se reasigna «salvo `was_master`» | **SOBREAFIRMADO** | `drm_file.h:275-277`; sitio de llamada `SOURCE_NOT_LOCATED` |

## O · NOMBRES TÉCNICOS vs NOMBRES DEL PROYECTO

| `PROJECT_NAME` | `TECHNICAL_MEANING` | `ACTUAL_UNIT` | `IS_NAME_ACCURATE` | `PROBLEM` | `PROPOSED_SEPARATED_NAMES` | `IMPLEMENTATION_CHANGE_REQUIRED` |
|---|---|---|---|---|---|---|
| `card_node_complete` | cobertura del nodo, **solo** | nodo | sí | ninguna: ya no mezcla atribución | — | NO |
| `render_node_complete` | ídem | nodo | sí | ninguna | — | NO |
| `drm_fds_enumerated` | enumeración + legibilidad de FDs | FD | sí | ninguna | — | NO |
| `DRM_ATTRIBUTION_FIELDS` | — | — | — | **RESUELTO**: 0 refs | `drm-client-id`→C · `drm-pdev`→D · `pasid`→I | NO |
| `clients_pasid_attributable` | — | — | — | **RESUELTO**: solo la anotación de retiro | `C` + `I`, por separado | NO |
| **`card_clients`** | conteo de **FDs** con `drm-client-id` presente | **FD** | **NO** | el nombre afirma clientes; además **presencia** etiquetada como **cantidad** | `card_drm_client_id_fds` (unidad explícita) | **YES** |
| **`render_clients`** | ídem | **FD** | **NO** | ídem | `render_drm_client_id_fds` | **YES** |

`NAME_COMPOSITE = YES` para `card_clients` y `render_clients`: el nombre compone «cliente» (entidad
no observada) con un valor que es un **conteo de FDs**, y convierte `PRESENCE` en cantidad.

## P · `PROJECT_MAPPING` = `NOT_ATTEMPTED`

Ninguna de las 9 propiedades tiene obligatoriedad asignada. `ANY_ALL = NOT_DECIDED` (y F muestra por
qué: la **clave** depende de `C-4`, no de una decisión de `any()`/`all()`).
`PASS_FAIL = NOT_DEFINED`. `TECHNICAL_MODEL_STATUS = CLOSED`:
9 propiedades con semántica independiente, 0 agregadas, 15 entidades diferenciadas, 10 relaciones con
dirección y unidad, 11 no-equivalencias refutadas, 10 falsificadores válidos, 1 `PROVISIONAL` por
falta de fuente, 3 límites de fuente declarados, 9 errores históricos corregidos.
Lo abierto y **deliberadamente nociuiente**: `C-4` (`CONFLICT_UNRESOLVED`), `C-1`/`C-2`
(`CONFLICT_UNRESOLVED`), amdgpu (`SOURCE_INCOMPLETE`), `VALUE` de `client_id` (`NOT_AVAILABLE`).
Ninguna se cierra por investigación adicional: no hay fuente que las resuelva.

## Q · `CANONICAL_PROPERTY_NAMES` y clasificación de cada aparición

### Q.1 · Nombres canónicos (10 enumerados → 9 propiedades + 1 `SPLIT`)

| | Nombre canónico | `ENTITY`/`UNIT` | `SOURCE` | `STATUS` |
|---|---|---|---|---|
| A | `DRM_CLIENT_IDENTITY` | `struct drm_file` / un `drm_file` | `drm_file.c:142,942-943`; spec `:64-72` | `ESTABLISHED` · `VALUE` `NOT_AVAILABLE` |
| B | `DRM_PROCESS_ASSOCIATION` | relación `drm_file`↔proceso | `drm_file.c:143`; `drm_file.h:271-278` | `ESTABLISHED` · `NOT_IMPLEMENTED` |
| C | `DRM_PCI_DEVICE_IDENTITY` | dispositivo / BDF | `drm_file.c:948-950`; spec `:59-62` | `ESTABLISHED` |
| D | `DRM_FD_OBSERVABILITY` | proceso + FD | `/proc/<pid>/fd`, `fdinfo` | `ESTABLISHED` |
| **E** | `DRM_CLIENT_USAGE_STATS` | — | — | **`SPLIT` — NO es una propiedad.** Es el contenedor que se divide en F y G |
| F | `DRM_MEMORY_ASSOCIATION` | agregado por `drm_file` y región | `drm_file.c:828-840`; spec `:140-175` | `ESTABLISHED` · `NOT_OBSERVED` |
| G | `DRM_ENGINE_USAGE` | `drm_file`×engine / ns acumuladas | spec `:79-137` | `ESTABLISHED` · `NOT_OBSERVED` |
| H | `DRM_VM_PASID_ASSOCIATION` | vmid | — | `SOURCE_INCOMPLETE` · `PROVISIONAL` |
| I | `GPU_PAGE_FAULT_CLIENT_IDENTITY` | bloque del motor | — | `SOURCE_INCOMPLETE` |
| J | `DRM_GEM_OBJECT_ASSOCIATION` | `drm_gem_object` / un objeto | `drm_file.h:299-304`; `drm_gem.h` | `PARTIALLY_ESTABLISHED` |

**Fuera de esta lista, por no ser una propiedad de entidad DRM**: `NODE_COMPLETENESS` es una propiedad
de **cobertura de barrido** (`HUMAN_BASIS: EXPLICIT`), no una propiedad de entidad kernel. Sigue
definida en §4-A y no se fusiona con ninguna de las diez.

### Q.2 · Clasificación de cada aparición del concepto retirado

| Apariencia | Decisión | Motivo |
|---|---|---|
| `attributable` (frase humana) | **`HISTORICAL_ONLY`** | término retirado; se conserva solo como procedencia |
| `ATTRIBUTABLE` como identificador | **`DEPRECATE`** | 0 en código; protegido por `test_ownership_criterion_contract.py` |
| `DRM_ATTRIBUTION_FIELDS` | **`SPLIT`** | 3 dominios → A (`client-id`), C (`pdev`), H (`pasid`) |
| `card_attributable` / `render_attributable` / `node_attributable` | **`SPLIT` → `DEPRECATE`** | predicate compuesto → `NODE_COMPLETENESS` (cobertura) |
| `clients_pasid_attributable` | **`SPLIT` → `DEPRECATE`** | unía `client` y `PASID` → A y H, por separado |
| `card_clients` / `render_clients` | **`RENAME`** | ya ejecutados → `card/render_drm_client_id_fds` (unidad FD) |
| `attribution` (nivel de evidencia) | **`KEEP`** | no es una propiedad: es el 4º nivel de `PRESENCE→VALUE→DISCRIMINATION→ATTRIBUTION` |
| `client attribution` en prosa | **`RENAME`** | 7 entidades «client» con nombre propio (Q.3) |
| `ATTRIBUTION_TO_DRM_CLIENT` / `_PROCESS` / `_PCI_NODE` / `_OBSERVED_FD` | **`HISTORICAL_ONLY`** | alternativas de objeto nunca elegidas; mapean a A, B, C, D |
| `DEBUGFS_CLIENT_ATTRIBUTION` | **`KEEP`** | nombre de recurso del **kernel** (`drm_debugfs.c:143`), no paraguas |
| `drm_client_debugfs_init` | **`KEEP`** | símbolo del kernel; `SOURCE_INCOMPLETE` en su semántica |
| `drm_client_dev` | **`KEEP` + `UNKNOWN`** | **no es entidad de kernel**: solo `drm_client_dev_restore(dev)` (`:391`), definición `SOURCE_NOT_LOCATED` |
| `"card1 / 8 attributable client(s)"` en bundle | **`HISTORICAL_ONLY`** | artefacto preservado; no se reescribe |

### Q.3 · Siete conceptos «client», siete nombres

`struct drm_file` · `debugfs_client_entry` (1 fila = 1 `drm_file`) · `drm_master` ·
`gpu_page_fault_client_id` (I) · `accel_minor_file` (`drm_is_accel_client`) · `drm_client_dev`
(sin fuente) · `drm_client_id` (clave fdinfo, 1:1 con `struct drm_file`).

### Q.4 · Prohibiciones, escritas

`drm-client-id ≠ FD` · `≠ PID` · `≠ PASID` · `≠ GPU page-fault client-id` ·
`drm-pdev ≠ client identity` · `PASID ≠ drm-client-id` · `PASID ≠ PID` ·
`GEM object ≠ process` · `engine usage ≠ process identity` · `memory stats ≠ process memory` ·
`#FD ≠ #drm_file ≠ #drm-client-id ≠ #procesos` · `EMPTY_UNIVERSE ≠ ALL_OBSERVED_SATISFY ≠ NO_EVIDENCE`.

`PROJECT_MAPPING = NOT_ATTEMPTED` · `PASS_FAIL = NOT_DEFINED` · `ANY_ALL = NOT_DECIDED` ·
`HUMAN_REQUIREMENT = AMBIGUOUS/MIXED` · `CODE_CHANGE = NO` en esta sección.

## R · DISPOSICIÓN FINAL

```
SEMANTIC_DEFECT              = CONFIRMED
HUMAN_INTENT                 = UNDETERMINED        (y no se intentará determinarlo)
TECHNICAL_PROPERTIES         = SEPARATED_AND_DEFINED
DISPOSITION                  = CLOSE_AS_SEMANTICALLY_CORRECTED
IMPLEMENTATION_CHANGE_REQUIRED = YES   (1 pendiente, no autorizado)
PROJECT_MAPPING              = NOT_ATTEMPTED
CODE_CHANGE_THIS_ROUND       = NO
```

### R.1 · Verificación independiente (7 puntos)

| # | Intento de refutación | Resultado |
|---|---|---|
| 1 | ¿la propiedad original mezclaba conceptos? | **CONFIRMADO** — 4 fuentes, 10 unidades, 5 entidades «client» en el propio kernel |
| 2 | ¿cada propiedad nueva tiene unidad y entidad coherentes? | **CONFIRMADO** — 9 entidades distintas (`drm_file`, nodo, dispositivo, FD, relación, vmid, `drm_file`×engine, bloque, objeto GEM) + `NODE_COMPLETENESS` como cobertura |
| 3 | ¿se perdió información relevante? | **NO** — las 10 unidades de la frase original tienen fila; nada se descartó sin registro |
| 4 | ¿se introdujo una interpretación humana nueva? | **NO** — 7 de 9 son `AGENT_DERIVED`; 2 tienen cita literal; `OWNERSHIP_VERDICT` es `PROJECT_VERDICT` |
| 5 | ¿algún nombre sobreafirma semántica? | **NO** — `drm_client_dev` queda `NOT_ESTABLISHED`; `*_seen` documentado como `POOLED`; `active_gpu_drm_fds` nombra su unidad |
| 6 | ¿las propiedades se falsan independientemente? | **SÍ** — 10 falsificadores válidos, 1 `PROVISIONAL` por falta de fuente |
| 7 | ¿el modelo sigue independiente del proyecto? | **CONFIRMADO** — este documento no asigna **ningún veredicto** `PASS`/`FAIL` de proyecto: §T usa `STATUS` (`REQUIRED`/`OPTIONAL`/`NOT_DETERMINED`), no estados de veredicto. `PROJECT_MAPPING` no retrojustifica ninguna propiedad |

**Sobre la 4**: los dos intentos de refutación que Cleanup quedaba abierto en rondas previas
(`drm_client_dev` como entidad de kernel, `drm-memory-<region>` inexistente) ya se resolvieron: el
primero es `NOT_ESTABLISHED`, el segundo **existe** en la spec (`:143`). Ninguno sobrevivió.

### R.2 · Diagrama

```
REQUISITO HUMANO ORIGINAL  ("complete attributable evidence")
          |
          v
   [CONCEPTOS MEZCLADOS]   4 fuentes · 10 unidades · 5 "client" en el kernel
          |
    +-----+-----+-----+-----+-----+-----+-----+-----+-----+
    |     |     |     |     |     |     |     |     |     |
    v     v     v     v     v     v     v     v     v     v
  PROP A PROP B PROP C PROP D PROP E PROP F PROP G PROP H PROP I
    |     |     |     |     |     |     |     |     |     |
    v     v     v     v     v     v     v     v     v     v
 defin. defin. defin. defin. defin. defin. defin. defin. defin. defin.
  (FD) (proc)  (PCI) (file) (dev)  (mem) (eng) (PASID)(flt)  (GEM)
    |     |     |     |     |     |     |     |     |     |
    +-----------+-----+-----+-----+-----+-----+-----+-----+-----+
                          |
                          v
              MODELO TECNICO SEPARADO  (9 propiedades + NODE_COMPLETENESS)
                          |
                          v
               IMPLEMENTACION  (posterior, 1 cambio autorizado ya hecho)
```

## S · `REPLACEMENT` — la formulación humana, sustituida por el conjunto separado

```
HUMAN_FORMULATION   = "complete, attributable evidence" para card1/renderD129
HUMAN_FORMULATION_STATUS = REPLACED_AS_MIXED_CONCEPTS
SUSTITUYE          = las 7 propiedades canónicas de abajo + NODE_COMPLETENESS
ATTRIBUTION_TARGET = UNDEFINED_BY_HUMAN_REQUIREMENT   (no se infiere)
PROJECT_MAPPING    = NOT_ATTEMPTED
CODE_CHANGE        = NO   (esta sección)
NEXT               = REVIEW_SEPARATED_MODEL  (ya ejecutado: §R.1, 7/7 sin brecha)
```

### S.1 · Propiedades que sustituyen la formulación

| # | `NAME` | `MEANING` | `ENTITY`/`UNIT` | `SOURCE` | `OBSERVABILITY` | `LIMITS` | `FALSIFIER` | `PROVENANCE` |
|---|---|---|---|---|---|---|---|---|
| 1 | `DRM_NODE_COMPLETENESS` | la población relevante de procesos fue examinada respecto de los nodos, con la cobertura exigida | proceso × nodo DRM | los 4 términos de visibilidad de `/proc` | E·R·O observadas; P parcial | no cubre el minor `ACCEL`; cobertura parcial ≠ completa | mismo universo y privilegio con los 4 términos y una fila ausente | `HUMAN_REQUIREMENT` («complete», «FD visibility») |
| 2 | `DRM_CLIENT_IDENTITY` | identidad de la apertura DRM | `struct drm_file` / un `drm_file` | `drm_file.c:142,942-943`; spec `:64-72` | E sí · R presencia sí, **valor no** | unicidad global **o** por dispositivo (`C-4`); contador `static` de módulo | dos `drm_file` con el mismo `client_id` en el dominio de unicidad | `AGENT_DERIVED` (base: token retirado «client») |
| 3 | `DRM_PROCESS_ASSOCIATION` | el proceso que **está usando** esa apertura | relación `drm_file`↔TGID | `drm_file.c:143`; `drm_file.h:271-278`; `drm_debugfs.c:98-103` | E sí (debugfs) · R no implementado | **mutable**; no es la identidad del opener; sitio de reasignación `SOURCE_NOT_LOCATED` | `drm_clients_info` sin columna `tgid`; o `:272` describiendo al proceso original | `AGENT_DERIVED` |
| 4 | `DRM_PCI_DEVICE_IDENTITY` | dirección PCI del dispositivo DRM | dispositivo / BDF | `drm_file.c:948-950`; spec `:59-62` | E condicional (`dev_is_pci`) · R sí | no transporta vendor/device/class; no identifica cliente | `drm-pdev` no-BDF | `HUMAN_REQUIREMENT` («identified by PCI identity») |
| 5 | `DRM_PASID_VM_ASSOCIATION` | relación VM↔PASID↔proceso | vmid | **sin fuente obtenida** | E **no** | **`SOURCE_INCOMPLETE`** · `PROVISIONAL` | `pasid` junto a PID sin fault concurrente | `INFERENCE` |
| 6 | `DRM_MEMORY_ATTRIBUTION` | estadísticas de memoria de ese `drm_file` | agregado por file y región | `drm_file.c:828-840`; spec `:140-175` | por driver · `NOT_OBSERVED` | `=0` no prueba no-uso; no es inventario ni memoria de proceso | clave indexada por proceso en la spec | `AGENT_DERIVED` |
| 7 | `DRM_ENGINE_ACTIVITY` | tiempo de engine ejecutando trabajo de ese cliente | `drm_file`×engine / ns | spec `:79-137` (`:86`, `:88-89`) | por driver · `NOT_OBSERVED` | **no monótona**; no es actividad instantánea | `drm-engine-*` por proceso, o declarada monótona | `AGENT_DERIVED` |

**Los 7 no forman una cadena.** No hay `any()`/`all()` que los una, ni una condición compuesta, ni una
tabla de campos heterogéneos. Cada uno se investiga, verifica y modifica por separado.

## T · `PROJECT_MAPPING` — capa separada

`TECHNICAL_MODEL → PROJECT_REQUIREMENTS → PROJECT_MAPPING`. Esta sección **no altera** §A–§S.
`PASS/FAIL` del proyecto **no** se deriva de aquí: se deriva de la decisión humana de §S/T-1.

### T.1 · Decisiones humanas incorporadas

| | |
|---|---|
| `OWNERSHIP` | `DRM_NODE_COMPLETENESS` y `DRM_PCI_DEVICE_IDENTITY` quedan bajo el criterio humano ya documentado. No se inventa criterio técnico adicional |
| `AGENT_DERIVED` | `DRM_CLIENT_IDENTITY`, `DRM_PROCESS_ASSOCIATION`, `DRM_MEMORY_ATTRIBUTION`, `DRM_ENGINE_ACTIVITY` usables como propiedades del modelo, manteniendo la marca `AGENT_DERIVED` |
| `INFERENCE` | `DRM_PASID_VM_ASSOCIATION` permanece `INFERENCE` + `SOURCE_INCOMPLETE` |

### T.2 · Mapeo, con evidencia del proyecto medida en el collector `06a43d08`

| `PROJECT_REQUIREMENT` | `TECHNICAL_PROPERTY` | `RELATION` | `PROJECT_EVIDENCE` | `TECHNICAL_EVIDENCE` | `STATUS` | `PROVENANCE` | `LIMITS` | `OPEN_QUESTION` |
|---|---|---|---|---|---|---|---|---|
| criterio de ownership (filas `card/render_node_complete`, `user/root_namespaces_covered`, `drm_fds_enumerated`) | `DRM_NODE_COMPLETENESS` | **sostiene 5 de 10 filas** en su `STATE` | `ROOT_FD_COVERAGE 283/283`; `0` denegados; `drm_fds_enumerated` con guard `races > absent → UNKNOWN` | `/proc` + los 4 términos de visibilidad | **`REQUIRED`** | `HUMAN_REQUIREMENT` | no cubre el minor `ACCEL`; cobertura parcial ≠ completa | ¿el universo debe incluir `ACCEL`? |
| criterio de ownership (identidad del dispositivo) | `DRM_PCI_DEVICE_IDENTITY` | **sostiene `gpu_proven`**, que condiciona 3 filas y `drm_fd_enumeration_state` | `GPU_IDENTITY_STATUS = PROVEN`, `0000:01:00.0`, `0x1002:0x699f`, `drm_discovery.agreement = true` | `drm-pdev` / sysfs | **`REQUIRED`** | `HUMAN_REQUIREMENT` | `drm-pdev` no transporta vendor/device/class | ninguna |
| — (ningún requisito la nombra) | `DRM_CLIENT_IDENTITY` | 10 referencias, **0 en `STATE`**; solo en `EVIDENCE` | contadores `*_drm_client_id_fds` (presencia por FD) y `drm_client_id_seen` (pooled) | `drm-client-id` presente en fdinfo | **`OPTIONAL`** | `AGENT_DERIVED` | `VALUE` nunca preservado: `PRESENCE` sí, `VALUE` `NOT_AVAILABLE` | ¿debe activarse al exigir identidad de apertura? |
| — | `DRM_PROCESS_ASSOCIATION` | **0 referencias** a `tgid`; carrier debugfs no implementado | ninguna | `drm_debugfs.c:92,98-103` expone `tgid` | **`OPTIONAL`** | `AGENT_DERIVED` | no implementado en el proyecto | ¿se necesita `drm_file`↔proceso, dado que FD→proceso ya se observa? |
| — | `DRM_MEMORY_ATTRIBUTION` | **0 referencias** en el collector | ninguna | spec `:140-175` | **`OPTIONAL`** | `AGENT_DERIVED` | por driver; `NOT_OBSERVED` | ¿el proyecto necesita accounting? |
| — | `DRM_ENGINE_ACTIVITY` | **0 referencias** en el collector | ninguna | spec `:79-137` | **`OPTIONAL`** | `AGENT_DERIVED` | por driver; `NOT_OBSERVED`; `=0` no prueba no-uso | ídem |
| — | `DRM_PASID_VM_ASSOCIATION` | 20 referencias al **contador de presencia** `pasid`, no a la relación | contador `drm_pasid_seen` / `*_pasid_fds` | **`SOURCE_INCOMPLETE`** | **`NOT_DETERMINED`** | `INFERENCE` | la semántica de `pasid` no está obtenida | falta fuente primaria de amdgpu; **no** se infiere |
| — | las 5 filas del criterio antes **sin ficha** (`writers_resolved`, `agents_absent`, `pm_observed`, `guard_and_restore`, `btrfs_identity`) | — | **0 de 5** las sostiene una propiedad del modelo DRM; emiten `STATE` en **capas ajenas** (R1/R2/R3, storage) | ver **§T.5** | **`NOT_APPLICABLE`** al modelo DRM; estado propio por fila en §T.5 | `HUMAN_REQUIREMENT` parcial (lista de 15 ítems, `AGENTS.md:242-248`) + `AGENT_FORMALIZATION` | sin unidad propia en 3 de 5; `SOURCE="-"` en 2 de 5 | §T.5 §F-1…§F-7: **no les falta ficha DRM, les falta ficha en su propia capa** |

### T.3 · Lectura del mapeo

- **2 `REQUIRED`**, ambas `HUMAN_REQUIREMENT`: son las únicas que sostienen un `STATE` y las únicas
  con cita literal. **El criterio de ownership es evaluable hoy con esas dos.**
- **4 `OPTIONAL`**: capacidades del modelo **sin uso efectivo** — 0 en `STATE`, y 2 de ellas con 0
  referencias en el código. No se vuelven requisitos por el hecho de existir.
- **1 `NOT_DETERMINED`**: `DRM_PASID_VM_ASSOCIATION` por `SOURCE_INCOMPLETE` — **sin cambio**.
- **5 filas antes `NOT_DETERMINED`, resueltas en §T.5** como **`NOT_APPLICABLE`** al modelo DRM: 0 de 5
  se sostienen en una propiedad de §S. 1 (`pm_observed`) tiene `DEPENDS_ON: DRM_PCI_DEVICE_IDENTITY`
  por `SKIPPED_IDENTITY_NOT_PROVEN`; las otras 4 `RELATION = NONE_DECLARED`, 0 referencias. Tres tienen
  `STATE` constante por construcción, luego no pueden sostener ni refutar propiedad alguna.
- **0 `REQUIRED` nuevas**: ninguna necesidad del proyecto retrojustifica una propiedad técnica.
  `AGENT_DERIVED` **no** se reescribió como requisito, e `INFERENCE` **no** se convirtió en observación.
- `ATTRIBUTION_TARGET` sigue **`UNDEFINED_BY_HUMAN_REQUIREMENT`**.

### T.4 · Capas que siguen separadas

`PROJECT_MAPPING = DETERMINED` para 6 de 8 filas. `TECHNICAL_MODEL` no cambió: `CODE_CHANGE = NO`.


### T.5 · Las 5 filas del criterio: ficha por capa, no por modelo DRM

Investigación de las 5 filas que §T.2 marcaba `NOT_DETERMINED`. Fuentes: `privileged_read_collector.py`
`06a43d0843957f36` (constantes, predicados y contexto), artefacto preservado
`FASE-C1-RUNTIME-PREFLIGHT/R1-20260926T030435Z.json` (`AGENTS_OWNERSHIP_MATRIX.conditions[]`),
`OWNERSHIP-AUDIT-HOST-C/R1-COLLECTOR-INDEPENDENT-REVIEW-2-20260926.md:92-106`,
`R1-C1-CORRECTION-CLOSURE-20260926.md:437-450`, `AGENTS.md:242-248` y `AGENTS.md § Recovery`.
`CODE_CHANGE = NO` · `TEST_CHANGE = NO` · las 7 propiedades de §S **no** se tocaron.

Convención de `STATUS`: `<clase> (modelo DRM) · <clase> (contrato propio de la fila)`.

| FIELD | EXISTENCE | MEANING | UNIT | LAYER | TECHNICAL_PROPERTY | RELATION | EVIDENCE | STATUS | PROVENANCE | LIMITS | OPEN_QUESTION |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `writers_resolved` | `OBSERVED` · collector:1600 `OWNERSHIP_CRITERION_ROWS[5]`; :1614 `OWNERSHIP_EXTERNAL_ROWS`; artefacto `conditions[writers_resolved]`; 5 tests lo fijan | descripción literal «governor, IRQ, scheduler, read-ahead and storage writers resolved»: **conjunción de 5 subsistemas**, no una unidad | `NOT_DECLARED` — `STATE` constante `NOT_EVALUATED`; `EVIDENCE` = frase de ruta; `SOURCE` = `-` | writer audit / control del entorno · ruta **R2** | **ninguna** de las 7. La descripción no incluye escritores de nodos DRM: esos están en `drm_fds_enumerated` y `DRM_NODE_COMPLETENESS`. `DRM_ENGINE_ACTIVITY` trata motores GPU, no escritores de subsistema | `NONE_DECLARED` · 0 referencias · no depende de `gpu_proven` | collector 1600/1614/1894; artefacto `STATE=NOT_EVALUATED`, `ROUTE=R2`; REVIEW-2 fila 6: `PASS` **imposible** | `NOT_APPLICABLE` (modelo DRM) · `UNIT_NOT_DECLARED` (contrato propio) | `AGENT_FORMALIZATION` del nombre; antecedente humano más cercano = sustantivo «writers» en la lista de 15 ítems, **sin definición** | no evaluable; `FULL` inalcanzable mientras siga `NOT_EVALUATED` (REVIEW-2) | ¿se descompone en 5 filas, una por subsistema, cada una con unidad y fuente? No se decide: exigiría 5 fichas y cambio de contrato del productor |
| `agents_absent` | `OBSERVED` · collector:1802/1843/1853; :2321-2331 `ActiveState in (active, activating, reloading)` + `MainPID`; :2854; artefacto `STATE=FAIL`, `EVIDENCE=«5 active service row(s)»`, `SOURCE=«systemctl show (read-only)»`; :2988 `g03`; :3342 `final.definition` | descripción «no active writer/agent during the window»; predicado real `active_agents == 0` | **conteo de unidades de servicio systemd activas** (entero sin dimensión). No es conteo de procesos: cuenta una fila de servicio aunque su `MainPID` sea `0` | preflight / estado del entorno · **R1** | **ninguna**. No-equivalencia **evidenciada**: su fuente es `systemctl show`; las 7 propiedades se alimentan de `/proc`, fdinfo, debugfs o sysfs del PCI | `NONE` con las 7 · sí **gatea** dentro del artefacto: `g03` y `final` (`root_visibility_complete and active_gpu==0 and active_storage==0 and active_agents==0`) | collector 2321-2331/2854/1802/1843/1853/2988/3342; artefacto `STATE=FAIL` | `NOT_APPLICABLE` (modelo DRM) · `MAPPED` localmente (unidad y fuente documentadas) | `AGENT_FORMALIZATION`; el término «agent» **no tiene antecedente en `AGENTS.md`** | **`CONFLICT_UNRESOLVED`**: la descripción dice «writer/**agent**» y la evidencia dice «N active **service row**(s)»; una fila de servicio no es un «agent» y «agent» no está definido en el proyecto. No se corrige | ¿«agent» = unidad systemd, proceso con FD DRM, o cliente? Sin definición, la fila solo puede pedir `active_agents == 0` | → **§T.6.1**: realidad medida determinable; término propuesto `candidate_service_units_active` |
| `pm_observed` | `OBSERVED` · collector:1506-1544 `pm_snapshot`; :2974 `pm_status = pm.get("PM_METRICS")`; :1803/1844/1854; artefacto `STATE=PASS`, `EVIDENCE=«PM_METRICS=READ»`, `pm.PM_METRICS=READ`, `pm_state=OBSERVED` | la fila afirma «PM state observed for the proven device»; el predicado real es `pm_status == "READ"`, es decir **que la lectura ocurrió**, no que el estado PM se observara | la fila **no** tiene unidad de medición: su valor es un **token de estado de lectura** (`READ` / `SKIPPED_IDENTITY_NOT_PROVEN`). El bloque `pm` sí tiene unidades, heterogéneas: `amdgpu_parameters.<p>.val` = valor del parámetro (unidad propia del parámetro), `.bytes` = bytes, `.truncated` = booleano, `.paths` = rutas | power management del dispositivo (sysfs) · **R1** | **ninguna** de las 7 | **`DEPENDS_ON: DRM_PCI_DEVICE_IDENTITY`** — única de las 5 con relación evidenciada: `pm_snapshot` devuelve `SKIPPED_IDENTITY_NOT_PROVEN` si `device_sysfs` está vacío (collector:1508) y `gpu_proven = GPU_IDENTITY_STATUS == "PROVEN"` (:1784). **No** es `DRM_NODE_COMPLETENESS`: no cuenta nodos ni FDs | collector 1506-1544/1508/1784/1803/1844/1854; `R1-C1-CORRECTION-CLOSURE:437-450`: «`PM_METRICS=READ` does NOT mean the whole PM surface was read… would read `PASS` with a third of the surface unreadable»; `power/*` = `OBSERVED`, superficie PM completa = `INCOMPLETE`/`LIMITATION`; «recorded, not changed» | `NOT_APPLICABLE` (modelo DRM) · `MAPPED` localmente (token + dependencia) con `LIMITATION` documentada | `HUMAN_REQUIREMENT` parcial: «PM» figura en la lista de 15 ítems de `AGENTS.md:242-248` | `PASS` significa «read(2) devolvió», **no** «estado PM observado»; superficie completa `INCOMPLETE` | ¿la fila debe expresar superficie leída (cobertura) en vez de token de lectura? Requiere cambio de contrato del productor → `CONTRACT_CHANGE_REQUIRED`, **no autorizado** |
| `guard_and_restore` | `OBSERVED` · collector:1603 `OWNERSHIP_CRITERION_ROWS[8]`; :1615 `OWNERSHIP_EXTERNAL_ROWS` = `NOT_EVALUATED`/`R3`; :1894; artefacto `STATE=NOT_EVALUATED`, `EVIDENCE=«guard/restore/recovery is a separate route; C1 is deferred»`, `SOURCE=-`; 5 tests | descripción «guard and restore proven»: **conjunción de 3 conceptos** (guard, restore, recovery) sin unidad | `NOT_DECLARED` — `STATE` constante; `EVIDENCE` = frase de ruta; `SOURCE` = `-` | **recuperación / restauración** · ruta **R3** · es la capa de `AGENTS.md § Recovery` | **ninguna**, y no debe crearse: no hay propiedad de restauración entre las 7 | `NONE_DECLARED` | antecedente humano **explícito** en `AGENTS.md § Recovery`: «an independent documented recovery path; TTY/recovery availability is an explicit gate» y «Define `RESTORE_PLANNED`, `RESTORE_EXECUTED` and `RESTORE_VALIDATED` separately» → 3 estados nombrados + 1 gate. La de mayor base humana de las 5 y la de menor evidencia: `C1` está `DEFERRED`, luego `RESTORE_EXECUTED` y `RESTORE_VALIDATED` **no existen** | `NOT_APPLICABLE` (modelo DRM) · `NOT_DETERMINED` (contrato propio: sin `SOURCE`, sin unidad, y `RESTORE_EXECUTED`/`RESTORE_VALIDATED` = `DEFERRED`) | `HUMAN_REQUIREMENT` parcial (`AGENTS.md § Recovery`) + `AGENT_FORMALIZATION` del nombre de fila | sin ruta R3 ejecutada la fila no puede dejar de ser `NOT_EVALUATED`; `FULL` inalcanzable (REVIEW-2 fila 11) | ¿los 3 estados `RESTORE_*` se mapean a filas de este criterio o a otro artefacto? No se decide: requiere autorización de `RUNTIME_EXECUTION` |
| `btrfs_identity` | `OBSERVED` · collector:1604; :1804; :1845; :1855; :2831 `btrfs_mounts = [line for line in mountinfo.splitlines() if " - btrfs " in line]`; :2972 `btrfs_status`; artefacto `STATE=NOT_APPLICABLE`, `EVIDENCE=«btrfs lines observed=ABSENT»`, `btrfs.matched_identity_same_window=NOT_AVAILABLE`, `mountinfo_btrfs_lines=[]` | descripción «Btrfs identity matched in the same window», pero el predicado **no compara identidades**: `NOT_APPLICABLE if btrfs_status != "PRESENT" else "UNKNOWN` — solo clasifica la **existencia de líneas btrfs** en mountinfo; nunca puede dar `PASS` | la fila no tiene unidad. `btrfs_status` ∈ {`PRESENT`,`ABSENT`} es un **token de presencia de líneas de texto** derivado de un filtro de cadenas. Junto: `storage_identity_evidence` = `STORAGE_METRICS=READ`, `block_sysfs=/sys/class/block/sdb3`, `identity.block_name=sdb3` | **storage + procedencia del host** | **ninguna**. La no-equivalencia con `DRM_PCI_DEVICE_IDENTITY` es **demostrable**: `GPU_BDF=0000:01:00.0` (PCI de display) vs `block_name=sdb3` (dispositivo de bloque); objetos, drivers y sysfs distintos | `NONE_DECLARED` · 0 referencias | collector 1604/1804/1845/1855/2831/2972; artefacto `NOT_APPLICABLE` + `matched_identity_same_window=NOT_AVAILABLE`; REVIEW-2 fila 9: `PASS` **nunca** | `NOT_APPLICABLE` (modelo DRM) · `NOT_APPLICABLE` (fila: no hay btrfs en la ventana) | `HUMAN_REQUIREMENT`: «Btrfs» figura en la lista de 15 ítems de `AGENTS.md:242-248` | su `NOT_APPLICABLE` es **ausencia tipo «condición no presente con lectura completa»**: el filtro corrió y devolvió 0 líneas — **no** es `COVERAGE_LOSS` (la lectura ocurrió) ni objeto ausente. `matched_identity_same_window=NOT_AVAILABLE` no se explica en la fila | ¿«identity matched» se implementará alguna vez, o la fila debe reformularse como presencia de btrfs? No se decide | → **§T.6.2**: realidad medida determinable; término propuesto `btrfs_mountinfo_lines_observed` |

#### T.5.1 · Hallazgos transversales

| # | Hallazgo | Evidencia |
|---|---|---|
| **§F-1** | **0 de 5** filas se sostienen en una propiedad del modelo DRM. §T.2 las etiquetó `NOT_DETERMINED` como si les faltara ficha **técnica DRM**: no les falta — les falta ficha en **su propia capa**, y 3 de ellas sí la tienen documentada | 0 referencias a las 7 propiedades en las 5 filas; §T.2 fila 8 |
| **§F-2** | única relación con el modelo: `pm_observed` `DEPENDS_ON DRM_PCI_DEVICE_IDENTITY` | collector:1508 + :1784 |
| **§F-3** | 3 de 5 tienen `STATE` **constante por construcción** (`writers_resolved`, `guard_and_restore` = `NOT_EVALUATED`; `pm_observed` = token de lectura). Un `STATE` constante no es una medición: no puede sostener ni refutar ninguna propiedad | REVIEW-2 filas 6, 8, 11 |
| **§F-4** | 2 de 5 tienen `SOURCE = "-"` (`writers_resolved`, `guard_and_restore`) y no pueden dejar de ser `NOT_EVALUATED` sin las rutas R2/R3 → **`FULL` es inalcanzable desde este collector** | REVIEW-2 agregado |
| **§F-5** | 2 de 5 tienen unidad coherente y documentada pero en capa ajena: `agents_absent` (unidades systemd) y `btrfs_identity` (token de presencia de líneas) | collector:2854, :2972 |
| **§F-6** | 2 `CONFLICT_UNRESOLVED` de nomenclatura, **no corregidos**: «agent» (descripción) vs «service row» (evidencia); «identity matched» (descripción) vs presencia de líneas btrfs (predicado) | collector:1601 vs 1843; 1604 vs 1804; §T.6.1, §T.6.2 |
| **§F-7** | el `NOT_APPLICABLE` de `btrfs_identity` es ausencia por **condición no presente con lectura completa**, no `COVERAGE_LOSS` ni objeto ausente — la distinción de 6 estados de `AGENTS.md § Measurement discipline` se respeta | collector:2831 (filtro ejecutado) |

#### T.5.2 · Lo que §T.5 NO hace

No crea ninguna propiedad técnica. No reassigna ninguna de las 7. No convierte `agents_absent` en
`DRM_CLIENT_IDENTITY` ni `DRM_PROCESS_ASSOCIATION` (fuente `systemctl show`, no fdinfo/debugfs); no
convierte `pm_observed` en `DRM_NODE_COMPLETENESS` (no cuenta nodos ni FDs); no convierte
`guard_and_restore` en propiedad DRM (no existe propiedad de restauración); no convierte
`btrfs_identity` en `DRM_PCI_DEVICE_IDENTITY` (dispositivo de bloque ≠ PCI de display). No decide las
descomposiciones pendientes. No ejecuta R2 ni R3. `OWNERSHIP` sigue `ADOPTED` sobre las 2 propiedades
humanas de `AGENTS.md:242-248`, que estas 5 filas **no** sustituyen.

### T.6 · Los 2 conflictos de nomenclatura: realidad medida y término propuesto

Alcance: **solo documentación**. `CODE_CHANGE = NO` · `TEST_CHANGE = NO` · no se ejecutó R2 ni R3 ·
sin sudo · sin workloads · sin commits. Los dos campos pertenecen a la **capa de entorno/procedencia**;
no se añade ninguna propiedad al modelo técnico y **§A–§S no se altera**. Ninguna de las dos filas se
convierte en `PASS`, ni su `UNKNOWN`/`NOT_AVAILABLE` se reescribe.

Convención de `STATUS`: `<clase> (sobreafirmación) · <clase> (término) · <clase> (brecha de requisito)`.

#### T.6.1 · `agents_absent`

| | |
|---|---|
| `CURRENT_TERM` | nombre de fila **`agents_absent`**; descripción literal en `OWNERSHIP_CRITERION_ROWS[6]` (collector:1601): «no active writer/agent during the window»; `EVIDENCE` (collector:1843): «N active service row(s)»; `SOURCE` (collector:1853): «systemctl show (read-only)» |
| `MEASURED_REALITY` | `systemctl show <unit> --no-pager --plain --property=Id,LoadState,ActiveState,SubState,MainPID,ExecMainPID,FragmentPath,ControlGroup,TriggeredBy,Triggers` ejecutado sobre una **lista fija y cerrada de 15 nombres de unidad** (collector:1248-1264: `system-autopilot.timer`, `system-autopilot.service`, `sys-tuned.timer`, `sys-tuned.service`, `kalm-gpu.service`, `kalm.service`, `kalm-lite.service`, `irqbalance.service`, `power-profiles-daemon.service`, `sysstat-collect.timer`, `sysstat-collect.service`, `crond.service`, `udisks2.service`, `kde-baloo.service`, `systemd-udevd.service`), **ámbito `system` únicamente** (no se invoca `--user`), y se cuentan las filas con `ActiveState ∈ {active, activating, reloading}` (collector:2327-2331). Artefacto: `ownership.active_service_rows` **n = 5**, p. ej. `irqbalance.service` con `ControlGroup=/system.slice/irqbalance.service`. **Unidad = conteo de unidades de servicio systemd candidatas.** No es conteo de procesos, ni de clientes DRM, ni de `drm_file`, ni de escritores |
| `SEMANTIC_OVERCLAIM` | **3 sobreafirmaciones, todas evidenciadas.** (a) «**agents**» es término técnico **sin definir** en el proyecto y denota un universo host-wide que la sonda **no cubre**: 15 nombres fijos, sin enumeración, sin `--user`. (b) La palabra «**writer**» de la descripción **no tiene ninguna evidencia en esta fila**: la auditoría de escritores es `writers_resolved`, ruta **R2**, `STATE=NOT_EVALUATED`, `SOURCE="-"`. (c) «**no active**» sugiere ausencia en el host; lo que la fila establece es ausencia **dentro de un conjunto candidato cerrado** y **solo en ámbito system** |
| `PROPOSED_TERM` | **`candidate_service_units_active`** — «número de unidades de servicio systemd, de un conjunto candidato fijo de 15 nombres, ámbito `system`, con `ActiveState ∈ {active, activating, reloading}`, en la ventana». Unidad: **conteo de unidades candidatas**. Se **retira** de la fila el término `agents`, por no definido |
| `STATUS` | `OVERCLAIM_CONFIRMED` · `MEASURED_REALITY_DETERMINED` · `PROPOSED_TERM_READY` · `REQUIREMENT_COVERAGE_GAP_OPEN` |
| `EVIDENCE` | collector:1247-1264 (lista fija), 1265-1291 (`systemctl show` y propiedades), 2320-2337 (`service_pids`, `ActiveState`), 2854 (`active_agents`), 1802/1843/1853 (predicado, evidencia, fuente), 2988 (`g03`), 3342 (`final.definition`); artefacto `ownership.active_service_rows` n=5. Dato adicional: `service_pids` (MainPID>0) **sí se consume** en collector:2610-2618 (`late_observed_pids`) y 2631-2638 (`relevant_ps`), pero eso **amplía la cobertura del inventario de pids**; no es la evidencia de la fila ni la convierte en medición de procesos |
| `REMAINING_DECISION` | **(1)** Adoptar el nombre nuevo es acto humano **y** exige tocar `OWNERSHIP_CRITERION_ROWS` y el diccionario `evidence` del collector: **no autorizado**. **(2)** El término propuesto nombra la entidad que el código ya enumera; **no redefine «agent»** ni lo declara sinónimo de otra cosa. **(3)** Si el requisito humano pretendiera ausencia host-wide de procesos/agentes, el nombre correcto **no** repara la fila: seguiría sin cubrir el universo. Es `REQUIREMENT_COVERAGE_GAP`: se registra y **no se cierra aquí** |

#### T.6.2 · `btrfs_identity`

| | |
|---|---|
| `CURRENT_TERM` | nombre de fila **`btrfs_identity`**; descripción literal (collector:1604): «Btrfs identity matched in the same window»; predicado (collector:1804): `NOT_APPLICABLE` si `btrfs_status != "PRESENT"`, si no `UNKNOWN` |
| `MEASURED_REALITY` | filtro de substring `" - btrfs "` sobre las líneas de `/proc/self/mountinfo` (collector:2831) → `btrfs_status ∈ {PRESENT, ABSENT}` (collector:2972). Artefacto: `mountinfo_btrfs_lines = []`, `btrfs_status=ABSENT` → `STATE=NOT_APPLICABLE`, `EVIDENCE=«btrfs lines observed=ABSENT»`. **La fila tiene 2 resultados y ninguno es `PASS`.** `matched_identity_same_window` es el **literal `"NOT_AVAILABLE"`** escrito en collector:2841: no se calcula, no se lee, y la fila **no lo consume**. Gate `G-08` lo declara `REQUIRED` con valor `NOT_AVAILABLE` y resumen «matched_identity_same_window NOT_AVAILABLE; no reconciliation run» (collector:3222, 3300); historial `C1-PREFLIGHT-20260925T055714Z.md:39` = `BTRFS=CONFLICT; same-window tuple unavailable` → `DEFERRED`. **Unidad = número de líneas de `/proc/self/mountinfo` que contienen el patrón `" - btrfs "`.** No hay identidad, ni matching, ni ventana |
| `SEMANTIC_OVERCLAIM` | **2 sobreafirmaciones.** (a) «**identity**»: no existe comparación de identidad en ninguna parte del código; la fila no lee `matched_identity_same_window`. (b) «**matched in the same window**»: no existe tupla ni comparación de ventana. El nombre afirma un matching **no implementado**. Y `matched_identity_same_window = NOT_AVAILABLE` es un **literal, no una lectura fallida**: no es `COVERAGE_LOSS` ni `RACE`, y **no se afirma que fuera observado** |
| `PROPOSED_TERM` | **`btrfs_mountinfo_lines_observed`** — «número de líneas de `/proc/self/mountinfo` que contienen el patrón `" - btrfs "`, en la ventana de lectura». Unidad: **conteo de líneas coincidentes**; estado: `PRESENT` (≥1) / `ABSENT` (0). Sin identidad, sin matching, sin ventana, sin tupla |
| `STATUS` | `OVERCLAIM_CONFIRMED` · `MEASURED_REALITY_DETERMINED` · `PROPOSED_TERM_READY` · `REQUIREMENT_COVERAGE_GAP_OPEN` |
| `EVIDENCE` | collector:2831 (filtro), 2841 (literal), 2972 (`btrfs_status`), 1604/1804/1845/1855 (fila), 3222 y 3300 (gate `G-08`); artefacto `btrfs.mountinfo_btrfs_lines=[]`, `btrfs.matched_identity_same_window=NOT_AVAILABLE`, `AGENTS_OWNERSHIP_MATRIX.conditions[btrfs_identity].STATE=NOT_APPLICABLE`; `C1-PREFLIGHT-20260925T055714Z.md:39`; `C1-PREFLIGHT-20260925T060029Z.json:6` (`"REQUIRED": "matched_identity_same_window"`); `DOCUMENTARY-RECONCILIATION-2026-09-25.md:255`. No-equivalencia con `DRM_PCI_DEVICE_IDENTITY` ya establecida en §T.5: `GPU_BDF=0000:01:00.0` (PCI de display) vs `identity.block_name=sdb3` (dispositivo de bloque) |
| `REMAINING_DECISION` | **(1)** Adoptar el nombre nuevo es acto humano y exige tocar collector y artefactos históricos: **no autorizado**. **(2)** `G-08` sigue `REQUIRED` + `NOT_AVAILABLE`; resolverlo exige reconciliación Btrfs = `RUNTIME_EXECUTION` / cambio de sistema: **prohibido**. Se preserva como `NOT_AVAILABLE`. **(3)** Si el requisito humano de `AGENTS.md:242-248` («Btrfs») exigiera **identidad** y no **presencia**, la fila actual **no satisface** el requisito: brecha de cobertura del requisito, no problema de nombre, y **no se cierra aquí** |

#### T.6.3 · Lo que §T.6 NO hace

No cambia ningún nombre en el collector ni en los tests: los dos términos propuestos son
`PROPOSED_TERM`, no adoptados. No implementa matching de identidad Btrfs. No introduce relación entre
Btrfs y `DRM_PCI_DEVICE_IDENTITY`. No convierte `active_agents == 0` en prueba de ausencia de procesos,
de writers o de clientes DRM. No ejecuta R2 ni R3. No añade propiedades al modelo técnico. No altera
§A–§S. No cierra ninguna de las dos brechas de requisito, que requieren decisión humana.

## U · `OWNERSHIP_HUMAN_FORMULATION` — cierre documental del criterio

Fuente humana: **`AGENTS.md:241-251`** ( Ownership ), texto literal citado abajo. `AGENTS.md`
**no se modifica** en esta ronda: la adopción es un acto humano.

> `FULL` requires complete attributable evidence for the RX550's card and render nodes, identified
> by PCI identity rather than by node name, plus user/root namespaces, DRM FDs, writers, agents, PM,
> governor, IRQ, scheduler, read-ahead, storage, Btrfs, guard and restore.
> If FD visibility is incomplete, a permission is denied, root namespaces are not covered, a client
> is active or a writer is unresolved, then `OWNERSHIP != FULL`. Use `PARTIAL` or `UNKNOWN`.

### U.1 · La formulación actual, medida contra las 6 preguntas

| # | Pregunta | Veredicto | Evidencia |
|---|---|---|---|
| 1 | ¿qué entidad debe demostrar ownership? | **`AMBIGUOUS`** | el texto dice evidencia *«for»* los nodos, nunca dice **de qué** es el ownership: del dispositivo, del nodo o del cliente. La palabra que lo resolvería es `attributable`, **retirada** |
| 2 | ¿sobre qué nodos/dispositivos? | **`UNAMBIGUOUS`** ✅ | «the RX550's card and render nodes, identified by PCI identity rather than by node name» |
| 3 | ¿qué evidencia mínima constituye ownership? | **`PARTIAL`** | enumera 15 ítems, pero los únicos calificadores son `complete` y `attributable`, **ambos defectuosos**: no hay regla de suficiencia |
| 4 | ¿qué estados son suficientes? | **`AMBIGUOUS`** | nombra `FULL`/`PARTIAL`/`UNKNOWN` sin regla que mapee evidencia → estado |
| 5 | ¿qué estados son insuficientes? | **`UNAMBIGUOUS`** ✅ | 4 condiciones explícitas → `OWNERSHIP != FULL` |
| 6 | ¿qué `UNKNOWN` debe permanecer `UNKNOWN`? | **`AMBIGUOUS`** | «Use `PARTIAL` or `UNKNOWN`» no dice *cuándo*; nada impide inferir una propiedad no establecida |

**Resultado: 2 inequívocas · 1 parcial · 3 ambiguas.** La modificación mínima es necesaria.

### U.2 · Tokens exigidos

```
OWNERSHIP_HUMAN_FORMULATION      = AGENTS.md:241-251 · AMBIGUOUS en 3 de 6 puntos · NO adoptada todavía
OWNERSHIP_REQUIRED_PROPERTIES    = DRM_NODE_COMPLETENESS (§S.1 #1) + DRM_PCI_DEVICE_IDENTITY (§S.1 #4)
OWNERSHIP_MINIMUM_EVIDENCE       = NO DEFINIDA por el texto humano.  PROPUESTA: ambos casos establecidos
                                    (AMBIGUOUS) para las 2 propiedades, sin inferencia de las demás
OWNERSHIP_INSUFFICIENT_EVIDENCE  = ADOPTADA tal cual: FD visibility incompleta · permiso denegado ·
                                    root namespaces no cubiertos · writer no resuelto · cliente activo.
                                    (4 condiciones, literales)
OWNERSHIP_UNKNOWN_CASES          = NO DEFINIDAS.  PROPUESTA: una propiedad no establecida permanece
                                    UNKNOWN; NO se infiere desde la presencia de un FD
OWNERSHIP_STATUS                 = REQUIREMENT_DECISION_REQUIRED · PROPOSED_FOR_HUMAN_ADOPTION
```

### U.3 · Modificación mínima propuesta — NO aplicada

| | |
|---|---|
| **Texto anterior** | «`FULL` requires **complete attributable evidence** for the RX550's card and render nodes, identified by PCI identity rather than by node name…» |
| **Texto nuevo propuesto** | «`FULL` requires, for the RX550's card and render nodes **identified by PCI identity rather than by node name**: **`DRM_NODE_COMPLETENESS` — complete coverage of the required node/FD universe, and `DRM_PCI_DEVICE_IDENTITY` — the node bound to the expected PCI device — both established (`ESTABLISHED`), not inferred from the mere presence of an FD**; a property that is not established remains `UNKNOWN`; plus user/root namespaces, DRM FDs, writers, agents, PM, governor, IRQ, scheduler, read-ahead, storage, Btrfs, guard and restore.» |
| **Razón exacta** | retira el término retirado `attributable` (única causa de la ambigüedad 1 y 3), declara la **unidad** de ownership (el nodo, ya presente en el texto), y fija que lo no establecido queda `UNKNOWN` (ambigüedad 6). Nada más |
| **Qué NO cambia** | las 2 propiedades y sus 8 campos · las 15 condiciones enumeradas · las 4 condiciones de insuficiencia · `PARTIAL`/`UNKNOWN` como estados · las otras 5 propiedades `AGENT_DERIVED` · `DRM_PASID_VM_ASSOCIATION` · el modelo técnico · `PROJECT_MAPPING` |
| **Reversibilidad** | total: es texto normativo, sin efecto sobre código, tests ni artefactos |
| **`OWNERSHIP_REQUIREMENT_CHANGE`** | 1 línea de `AGENTS.md`. **Requiere autorización humana explícita**; `AGENTS.md` está fuera de alcance en esta ronda |

### U.4 · Lo que esta sección NO hace

No convierte `DRM_CLIENT_IDENTITY`, `DRM_PROCESS_ASSOCIATION`, `DRM_PASID_VM_ASSOCIATION`,
`DRM_MEMORY_ATTRIBUTION` ni `DRM_ENGINE_ACTIVITY` en requisitos de ownership. No infiere ownership
desde la presencia de un FD. No convierte ausencia de evidencia en ausencia de ownership. No crea
condición compuesta. §A–§S intactas; §T sigue siendo capa de `PROJECT_MAPPING`.
