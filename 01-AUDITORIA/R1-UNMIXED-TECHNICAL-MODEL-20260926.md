# R1-UNMIXED-TECHNICAL-MODEL-20260926

`DOCUMENT_KIND` = `UNMIXED_TECHNICAL_MODEL` · **READ_ONLY + DOCUMENTACIÓN**
`TECHNICAL_MODEL_STATUS` = `CLOSED` (consolidado, no re-derivado) · `PROJECT_MAPPING` = `NOT_ATTEMPTED`
`CODE_CHANGE_REQUIRED` = `NO` · sin código, tests, `AGENTS.md`, `README.md`, commits, sudo,
systemctl, C1, benchmarks, GPU/sysfs/PM/storage.
Base reusada sin re-derivar: `R1-TECHNICAL-MODEL-CLOSURE` `ee86a3a7`,
`R1-SEMANTIC-DECOMPOSITION` `0801b7d9`, `R1-TECHNICAL-SEPARATION-TABLE` `116f011e`,
`R1-NORMATIVE-INVENTORY` `cbf2bbf8`. Fuentes primarias: linux **v6.12**, 12 ficheros.

## 1 · FINDING

El requisito humano no era necesariamente **incorrecto en cada observación individual**: el nodo
existía, el BDF se podía probar, los FDs se enumeraban. Lo que era defectuoso era
**técnicamentemixado/underspecified como una sola propiedad**: un único sustantivo
—«attributable»— con una sola palabra para ocho unidades distintas, y con «cliente» usado para
`drm_file`, `drm_master`, el bloque de page-fault y el proceso tenedor.

```
THE HUMAN REQUIREMENT WAS NOT NECESSARILY WRONG IN EACH INDIVIDUAL OBSERVATION,
BUT IT WAS TECHNICALLY MIXED/UNDERSPECIFIED AS A SINGLE PROPERTY.
CORRECTION = DECOMPOSITION
NOT_INTENT_RECONSTRUCTION · NOT_ARBITRARY_INTERPRETATION · NOT_GLOBAL_ANY · NOT_GLOBAL_ALL
NOT_PREMATURE_CODE_FIX
```

## 2 · HUMAN_REQUIREMENT_AS_WRITTEN

> `AGENTS.md:176-177` — `FULL` requires **complete attributable evidence** for the RX550's card and
> render nodes, **identified by PCI identity rather than by node name**
> `AGENTS.md:180-181` — If **FD visibility is incomplete**, **a permission is denied**, **root
> namespaces are not covered**, **a client is active** or **a writer is unresolved**, then
> `OWNERSHIP != FULL`

`PROVENANCE: HUMAN_REQUIREMENT`. `INTERPRETATION: MIXED_OR_UNDERSPECIFIED`.

## 3 · WHY_IT_IS_MIXED_OR_UNDERSPECIFIED

| # | Motivo, verificable |
|---|---|
| 1 | **Una palabra, ocho unidades**: FD, apertura DRM, dispositivo, vmid, bloque de motor, proceso, bytes, nanoseconds |
| 2 | **Cuatro fuentes**: `/proc/<pid>/fd`, `/proc/<pid>/fdinfo`, sysfs, debugfs |
| 3 | **«cliente» es ambiguo en el propio kernel**: cinco entidades lo nombran (`drm_file`, fila de `clients`, `drm_master`, page-fault `client-id`, minor `accel` vía `drm_is_accel_client`) |
| 4 | **La cláusula de fallo no discrimina estados**: «incomplete», «denied», «not covered», «unresolved» se expresan igual |
| 5 | **«evidence» sin portador declarado** |
| 6 | Definirlo por unión recrearía el defecto: la palabra ocultaría **cuál** de los ocho falló |

## 4 · DECOMPOSED_PROPERTIES (14) · 5 · TECHNICAL_DEFINITIONS

Estados solo justificados: `ESTABLISHED` · `PARTIALLY_ESTABLISHED` · `AMBIGUOUS` · `UNKNOWN` ·
`SOURCE_INCOMPLETE` · `CONFLICT` · `NOT_APPLICABLE`. **Sin `PASS`/`FAIL` de proyecto.**

### A · `NODE_EXISTENCE`
- `PROPERTY`: ¿existe y fue observado el nodo DRM objetivo?
- `DEFINITION`: el nodo `/dev/dri/<name>` existe y su entrada en `/dev` y sysfs es resoluble
- `ENTITY`: `drm_minor` · `UNIT`: un nodo
- `SOURCE`: sysfs `class/drm/`; `drm_discovery` (colector)
- `OBSERVABILITY`: `EXPOSED`
- `LIFETIME`: la del minor · `IDENTITY_SEMANTICS`: **no** portable: `cardN` no identifica entre hosts
- `MUTABILITY`: cambia si el driver reenumera · `KNOWN_LIMITS`: `cardN` ≠ identidad estable
- `WHAT_IT_PROVES`: que el nodo existe en este host
- `WHAT_IT_DOES_NOT_PROVE`: que sea el dispositivo objetivo; que tenga clientes; que esté en uso
- `FALSIFIER`: symlink a nodo ausente, roto, o a otro BDF → `NOT_ESTABLISHED`
- `PROVENANCE`: `KERNEL_IMPLEMENTATION` + `PROJECT_FORMALIZATION` (nombre)
- `STATUS`: **`ESTABLISHED`**

### B · `NODE_IDENTITY`
- `DEFINITION`: el nodo observado corresponde al dispositivo PCI objetivo
- `ENTITY`: `drm_device` / dispositivo PCI · `UNIT`: un dispositivo
- `SOURCE`: BDF→sysfs; `dev_is_pci`; `drm-pdev` (`drm_file.c:948-950`); spec `:59-62`
- `OBSERVABILITY`: `EXPOSED` (sysfs siempre; `drm-pdev` solo si el dispositivo es PCI)
- `LIFETIME`: la del dispositivo · `IDENTITY_SEMANTICS`: **BDF** `domain:bus:slot.func`
- `MUTABILITY`: inmutable · `KNOWN_LIMITS`: `drm-pdev` no transporta vendor/device/class
- `WHAT_IT_PROVES`: que el nodo pertenece al BDF esperado
- `WHAT_IT_DOES_NOT_PROVE`: identidad de cliente; nº de clientes; que exista un `drm_file`
- `FALSIFIER`: `drm-pdev` emitiendo algo que no sea `domain:bus:slot.func`
- `PROVENANCE`: `KERNEL_SPECIFICATION` + `KERNEL_IMPLEMENTATION`
- `STATUS`: **`ESTABLISHED`** (en este host: `PROVEN`, `0000:01:00.0`, `0x1002:0x699f`, `amdgpu`)

### C · `NODE_FD_VISIBILITY`
- `DEFINITION`: se pudo enumerar **y leer** la visibilidad de los DRM FDs del universo
- `ENTITY`: FD DRM / proceso · `UNIT`: **FD**
- `SOURCE`: `/proc/<pid>/fd/<n>` (symlink) + `/proc/<pid>/fdinfo/<n>`
- `OBSERVABILITY`: `EXPOSED`; lectura **verificada por `read_bytes`+`status`** (un error de lectura
  se registra como `READ_ERROR`, nunca como vacío)
- `LIFETIME`: la del FD · `IDENTITY_SEMANTICS`: un descriptor de proceso
- `MUTABILITY`: re-evaluable · `KNOWN_LIMITS`: depende del privilegio y del namespace
- `WHAT_IT_PROVES`: que el proceso **poseía** ese descriptor y que su fdinfo se pudo leer
- `WHAT_IT_DOES_NOT_PROVE`: que el FD sea un `drm_file`; identidad de cliente; actividad
- `FALSIFIER`: `read_text` (que degrada a `""`) usado en la ruta de fdinfo → protegido por test
- `PROVENANCE`: `PROJECT_FORMALIZATION` (nombre) sobre `KERNEL_IMPLEMENTATION`
- `STATUS`: **`ESTABLISHED`** (12 FDs / 4 procesos, `EUID 0`, cobertura `283/283`)

### D · `DRM_FILE_IDENTITY` (y K, el mismo par, dos caras)
- `DEFINITION`: la **cardinalidad** FD↔apertura: `FD → struct file` es **N:1**; `struct file →
  drm_file` es **1:1** (`private_data`)
- `ENTITY`: `struct drm_file` · `UNIT`: **una apertura DRM**
- `SOURCE`: `drm_file.c:936-950`; `drm_file.h:164-391`
- `OBSERVABILITY`: fdinfo **no** publica la identidad; el **core** sí, en
  `debugfs/dri/<minor>/clients`, una **fila por `drm_file`** (`drm_debugfs.c:92,98-103,143`)
- `LIFETIME`: `open()`→`close()`; **`dup()`/`fork()` no crean un `drm_file`**
- `IDENTITY_SEMANTICS`: `drm-client-id` es 1:1 conceptual con `struct drm_file`
  (spec `:66-68`); **varios FD pueden referenciar la misma apertura**
- `MUTABILITY`: el `drm_file` es inmutable; su `pid` **no** (§E)
- `KNOWN_LIMITS`: unicidad global **o** por dispositivo (`:70-71`) → `drm-pdev` necesario en el
  segundo caso; el core usa un contador `static` de módulo (`drm_file.c:132`), único dentro de la
  vida del módulo `drm`
- `WHAT_IT_PROVES`: que un FD pertenece a una apertura; y el **valor** de su identificador
- `WHAT_IT_DOES_NOT_PROVE`: que FD ≡ `drm_file`; que `client_id` sea PID, proceso, PASID,
  `drm_master` o page-fault `client-id`; el nº de clientes
- `FALSIFIER`: dos `drm_file` con el mismo `client_id`; o dos FDs del mismo `drm_file` con
  identificadores distintos
- `PROVENANCE`: `KERNEL_SPECIFICATION` + `KERNEL_IMPLEMENTATION`
- `STATUS`: **`ESTABLISHED`** (semántica) · el **valor** en este host: **`NOT_AVAILABLE`**
  — `PRESENCE` observada solo por cita documental, artefacto bruto `NOT_AVAILABLE`

### E · `PROCESS_ASSOCIATION`
- `DEFINITION`: qué proceso está asociado al `drm_file` según la fuente utilizada
- `ENTITY`: `struct drm_file.pid` · `UNIT`: TGID en el instante
- `SOURCE`: `drm_file.c:143` (`task_tgid(current)`); `drm_file.h:271-278`
  («Process that is **using** this file»); `drm_auth.c:233-244` lo compara con
  `task_tgid(current)`
- `OBSERVABILITY`: **`EXPOSED` por el core** vía debugfs (columna `tgid`); **no** por fdinfo
- `LIFETIME`: por instancia · `IDENTITY_SEMANTICS`: el proceso que **usa** el archivo, **no** el
  que lo abrió originalmente
- `MUTABILITY`: **mutable**, documentado en la fuente (`drm_file.h:275-277`); updater
  `drm_file.c:435`; **sitio de llamada `SOURCE_NOT_LOCATED`**
- `KNOWN_LIMITS`: dirección opuesta a «proceso que posee el FD» (§C): son relaciones distintas
- `WHAT_IT_PROVES`: que hay una asociación observable `drm_file` ↔ TGID
- `WHAT_IT_DOES_NOT_PROVE`: identidad histórica del opener; identidad del `drm_file`; actividad
- `FALSIFIER`: `drm_clients_info` sin columna `tgid`, o `drm_file.h:272` describiendo al proceso
  original
- `PROVENANCE`: `KERNEL_IMPLEMENTATION` + `KERNEL_SPECIFICATION`
- `STATUS`: **`ESTABLISHED`** (semántica) · **`NOT_IMPLEMENTED`** en el proyecto

### F · `PCI_DEVICE_ASSOCIATION`
- `DEFINITION`: qué dispositivo DRM/PCI corresponde al file observado
- `ENTITY`: `drm_file → drm_minor → drm_device → PCI` · `UNIT`: la relación
- `SOURCE`: `drm_file.minor` (`drm_file.h:295-296`); `drm-pdev`
- `OBSERVABILITY`: `EXPOSED` condicional (`dev_is_pci`)
- `LIFETIME`: la del file · `IDENTITY_SEMANTICS`: BDF del dispositivo **de su** minor
- `MUTABILITY`: inmutable · `KNOWN_LIMITS`: distinto de §B: §B identifica el **nodo**, §F la
  **relación file→dispositivo**; no son la misma propiedad
- `WHAT_IT_PROVES`: a qué dispositivo pertenece una apertura concreta
- `WHAT_IT_DOES_NOT_PROVE`: identidad de cliente
- `FALSIFIER`: dos `drm_file` del mismo dispositivo con `drm-pdev` distinto
- `PROVENANCE`: `KERNEL_IMPLEMENTATION` + `KERNEL_SPECIFICATION`
- `STATUS`: **`PARTIALLY_ESTABLISHED`**: solo existe un contador `drm-pdev` **pooled**, no una
  relación por file

### G · `PASID_ASSOCIATION`
- `DEFINITION`: qué significa técnicamente PASID en el contexto AMDGPU
- `ENTITY`: **vmid** · `UNIT`: vmid
- `SOURCE`: **`SOURCE_INCOMPLETE`** — 0 ocurrencias de `pasid` en `drm-usage-stats.rst`;
  0 en el core v6.12; convención de driver
- `OBSERVABILITY`: **`NOT_ESTABLISHED`**
- `LIFETIME` / `MUTABILITY`: `UNKNOWN`
- `IDENTITY_SEMANTICS`: **PASID NO es `drm-client-id`, NO es PID, NO es `drm_file`, NO es «cliente
  DRM»**. Son cuatro dominios distintos
- `KNOWN_LIMITS`: la relación VM↔PASID↔proceso es **episódica**: solo durante un page fault y con
  el proceso activo
- `WHAT_IT_PROVES`: nada en este host
- `WHAT_IT_DOES_NOT_PROVE`: identidad permanente de proceso; identidad DRM; cualquier equated con
  `drm-client-id`
- `FALSIFIER`: `pasid` impreso junto a un PID sin fault concurrente
- `PROVENANCE`: `UNKNOWN` (fuente de amdgpu inaccesible: 404 en 3 mecanismos)
- `STATUS`: **`SOURCE_INCOMPLETE`**

### H · `VM_ASSOCIATION`
- `DEFINITION`: qué relación puede establecerse entre VM, PASID y proceso
- `ENTITY`: VM / GPU address space · `UNIT`: espacio de direcciones
- `SOURCE`: `SOURCE_INCOMPLETE` (docs de amdgpu no obtenidas)
- `OBSERVABILITY`: **`NOT_ESTABLISHED`** · `LIFETIME` / `MUTABILITY`: `UNKNOWN`
- `IDENTITY_SEMANTICS`: una VM no es un proceso ni un `drm_file`
- `KNOWN_LIMITS`: **no se infiere el hueco**
- `WHAT_IT_PROVES`: nada en este host
- `WHAT_IT_DOES_NOT_PROVE`: que exista una relación permanente VM↔proceso
- `FALSIFIER`: una fuente que haga de la VM una identidad de proceso
- `PROVENANCE`: `UNKNOWN` · `STATUS`: **`SOURCE_INCOMPLETE`**

### I · `MEMORY_ACCOUNTING`
- `DEFINITION`: qué significan exactamente las estadísticas de memoria DRM por cliente
- `ENTITY`: `drm_file` · `UNIT`: **agregado por `drm_file` y región**
- `SOURCE`: `drm_print_memory_stats` (`drm_file.c:828-840`); spec `:140-175`
  (`:143 drm-memory-<region>`, `:155 shared`, `:160 total`, `:164 resident`, `:168 purgeable`,
  `:172 active`)
- `OBSERVABILITY`: **por driver**; el core emite las claves pero el relleno es del driver
- `LIFETIME`: derivada de `object_idr` · `IDENTITY_SEMANTICS`: estadística **del cliente**
- `MUTABILITY`: derivada · `KNOWN_LIMITS`: `=0` **no** prueba no-uso; no es inventario de objetos
- `WHAT_IT_PROVES`: consumo agregado de esa apertura por región
- `WHAT_IT_DOES_NOT_PROVE`: **memoria de un proceso**; que `=0` significase no-uso; inventario
- `FALSIFIER`: clave de memoria indexada por proceso en la spec
- `PROVENANCE`: `KERNEL_SPECIFICATION` + `KERNEL_IMPLEMENTATION`
- `STATUS`: **`ESTABLISHED`** (semántica) · **`NOT_OBSERVED`** en este host ·
  **`NOT_IMPLEMENTED`** en el proyecto (0 referencias)

### J · `ENGINE_ACCOUNTING`
- `DEFINITION`: qué significa exactamente `drm-engine-*`
- `ENTITY`: `drm_file` × engine · `UNIT`: ns **acumuladas** por engine
- `SOURCE`: spec `:79-137`; `:86` *«time the engine spent busy executing workloads belonging to
  **this client**»*; `:88-89` **no monótona**
- `OBSERVABILITY`: por driver · `LIFETIME`: contador acumulado del driver
- `IDENTITY_SEMANTICS`: tiempo **del cliente**, en el sentido de §D
- `MUTABILITY`: **no monótona**: ante un retroceso hay que retener el máximo
- `KNOWN_LIMITS`: **no** es estado instantáneo; `=0` **no** prueba no-uso
- `WHAT_IT_PROVES`: trabajo acumulado de esa apertura
- `WHAT_IT_DOES_NOT_PROVE`: **actividad actual del proceso**; identidad de proceso; inventario
- `FALSIFIER`: `drm-engine-*` indexada por proceso, o declarada monótona en la spec
- `PROVENANCE`: `KERNEL_SPECIFICATION` · `STATUS`: **`ESTABLISHED`** · **`NOT_OBSERVED`** ·
  **`NOT_IMPLEMENTED`**

### L · `FD_COUNT` (separación explícita de cuatro cantidades)
- `DEFINITION`: cantidad de **descriptores** observados
- `ENTITY`: FD · `UNIT`: FD
- `SOURCE`: `/proc/<pid>/fd/<n>`
- `OBSERVABILITY`: `EXPOSED` · `LIFETIME`: la del FD
- `IDENTITY_SEMANTICS`: `#FD ≠ #drm_file ≠ #drm-client-id ≠ #procesos`
  (`dup()`/`fork()` hacen que varios FD compartan una apertura)
- `MUTABILITY`: re-evaluable · `KNOWN_LIMITS`: `EMPTY_UNIVERSE ≠ ALL_OBSERVED_SATISFY_PROPERTY`
- `WHAT_IT_PROVES`: cuántos descriptores había
- `WHAT_IT_DOES_NOT_PROVE`: cuántos clientes, cuántos `drm_file`, cuántos procesos
- `FALSIFIER`: un mundo con 2 FD y 1 `drm_file`; y su inverso
- `PROVENANCE`: `KERNEL_IMPLEMENTATION` + `PROJECT_FORMALIZATION`
- `STATUS`: **`ESTABLISHED`**

### M · `DRM_MASTER`
- `DEFINITION`: qué relación de master existe
- `ENTITY`: `drm_master` · `UNIT`: un master
- `SOURCE`: `drm_lease.h`; `drm_lease.c`; `drm_auth.c:81` (`drm_is_current_master`);
  columna `master` de la fila debugfs (`drm_debugfs.c:92,105`)
- `OBSERVABILITY`: **por ioctl**, no por fdinfo
- `LIFETIME`: `kref` · `IDENTITY_SEMANTICS`: ownership/autenticación de **nodos primarios**
- `MUTABILITY`: **transferible** por leasing
- `KNOWN_LIMITS`: `NOT_APPLICABLE` en nodos no primarios
- `WHAT_IT_PROVES`: qué `drm_file` posee el master y si es el actual
- `WHAT_IT_DOES_NOT_PROVE`: identidad de cliente; identidad de proceso
- `FALSIFIER`: master transferido sin `lessor`
- `PROVENANCE`: `KERNEL_IMPLEMENTATION` + `KERNEL_SPECIFICATION`
- `STATUS`: **`ESTABLISHED`** · **`NOT_OBSERVED`** aquí

### N · `GEM/MEMORY_RELATION`
- `DEFINITION`: qué relación puede establecerse entre `drm_file` y objetos GEM
- `ENTITY`: `drm_gem_object` · `UNIT`: un objeto
- `SOURCE`: `drm_file.object_idr` (`drm_file.h:299-303` doc, `:304` campo, protegido por
  `table_lock` `:306`); mapea **handles de objeto `mm`** → punteros (`:302`); relación 1:N
- `OBSERVABILITY`: **no observable** desde espacio de usuario en las fuentes leídas
- `LIFETIME`: la del objeto · `IDENTITY_SEMANTICS`: un GEM **no** es un proceso, ni un cliente, ni
  un FD
- `MUTABILITY`: `object_idr` mutable (altas y bajas de handles)
- `KNOWN_LIMITS`: un GEM puede ser alcanzable desde varios `drm_file`; el idr pertenece al
  `drm_file`, **no** a un proceso
- `WHAT_IT_PROVES`: que los handles de esa apertura alcanzan objetos GEM
- `WHAT_IT_DOES_NOT_PROVE`: **GEM = proceso**; inventario; cualquier identidad de usuario
- `FALSIFIER`: una fuente que haga del GEM una identidad de proceso
- `PROVENANCE`: `KERNEL_IMPLEMENTATION`
- `STATUS`: **`PARTIALLY_ESTABLISHED`** (semántica del núcleo) · `NOT_OBSERVED` (exposición)

## 6 · PROVENANCE (recuento)

| | Origen | Propiedades |
|---|---|---|
| `HUMAN_REQUIREMENT` | «complete», «PCI identity», «FD visibility» | 3 fragmentos → N-1, N-2, N-3 |
| `KERNEL_SPECIFICATION` | `drm-usage-stats.rst` | D, F, I, J, M |
| `KERNEL_IMPLEMENTATION` | 12 ficheros v6.12 | A–F, I, L, M, N |
| `PROJECT_FORMALIZATION` | nombres A–N | **todos** los nombres de propiedad |
| `UNKNOWN` | amdgpu inaccesible | G, H |
| `INFERENCE` | — | **ninguna** en las 14 fichas |

Ningún nombre de propiedad tiene antecedente fuera del kernel o de la spec: los 14 son
`PROJECT_FORMALIZATION`, y su **semántica** es de kernel.

## 7 · CURRENT_PROJECT_ARTIFACTS_AFFECTED

Sin corregir. `CODE_CHANGE_NEEDED` refleja lo que haría falta, no lo que se hará.

| Artefacto | `CURRENT_MEANING` | `WHAT_IT_ACTUALLY_MEASURES` | `WHAT_IT_CLAIMS` | `MIXED_CONCEPTS` | `PROVENANCE` | `PROBLEM` | `REQUIRED_DECISION` | `CODE_CHANGE_NEEDED` |
|---|---|---|---|---|---|---|---|---|
| `DRM_ATTRIBUTION_FIELDS` | — | **ausente** (0 refs) | — | — | `AGENT_FORMALIZATION` | **RESUELTO**: eliminado; sus 3 camposDistributed a N-4, N-6, N-7 | ninguna | NO |
| `card_attributable` / `render_attributable` / `node_attributable` | — | **ausentes** (0 refs) | — | — | `AGENT_FORMALIZATION` | **RESUELTO**: eliminados | ninguna | NO |
| `clients_pasid_attributable` | anotación de retiro (línea 1606) | nada | — | — | `AGENT_FORMALIZATION` | **RESUELTO**: retirado; queda solo el comentario que lo declara retirado | ninguna | NO |
| **`card_clients`** (línea 2965) | «clientes en card1» | **conteo de FDs con la clave `drm-client-id` presente** | cantidad de clientes | **FDs nombrados como clientes**; además **presencia** etiquetada como **cantidad** | `PROJECT_FORMALIZATION` | **ABIERTO**: el nombre afirma `clients` y el valor es un conteo de FDs. El valor es correcto como presencia; el **nombre** miente | renombrar a `card_drm_client_id_fds` (unidad explícita) | **YES** |
| **`render_clients`** (línea 2966) | ídem | ídem | ídem | ídem | `PROJECT_FORMALIZATION` | **ABIERTO**, mismo defecto | ídem | **YES** |
| `drm_fds_enumerated` | enumeración de FDs DRM con legibilidad | exactamente eso: cobertura + legibilidad de FDs | — | **ninguno** (ya no mezcla atribución) | `PROJECT_FORMALIZATION` | **RESUELTO**: es solo cobertura; `EMPTY_UNIVERSE` protegido por el guard `races > absent → UNKNOWN` | ninguna | NO |

**Candidata a descomposición adicional**: ninguno de los 7 restantes mezcla ≥2 conceptos. El
defecto vivo es de **nomenclatura**, no de semántica (`card_clients`/`render_clients`).

## 8 · CONFLICTS_FOUND

| | `CLASS` |
|---|---|
| unicidad de `drm-client-id`: global o por dispositivo (spec `:70-71`; el core usa contador global de módulo) | `CONFLICT_UNRESOLVED` (`C-4`) |
| page-fault `client-id` = `drm-client-id` | `CONFLICT_UNRESOLVED` (`C-1`) |
| sentidos de `client` (cinco entidades) | `CONFLICT_UNRESOLVED` (`C-2`) |
| `D` vs `K`: misma pareja, dos caras (cardinalidad y valor) | **NO ES CONFLICTO**: son dimensiones distintas de la misma relación, ambas registradas |

`AMBIGUOUS` en ninguna ficha. `UNKNOWN` solo en G y H, por fuente ausente, no por ambigüedad.

## 9 · FALSIFIERS

14 fichas, 14 falsificadores, 3 de ellos **sin forma razonable de falsarlos** con las fuentes
disponibles → las partes afectadas quedan **`PROVISIONAL`**:

| Ficha | Falsificador | `STATUS` |
|---|---|---|
| D/K | dos `drm_file` con el mismo `client_id`; dos FDs del mismo `drm_file` con ids distintos | `AVAILABLE` |
| D/K unicidad | implementación por dispositivo con `client-id` repetido y `drm-pdev` presente | `AVAILABLE` |
| D/K alcance | `client_id` reiniciado tras recargar el módulo `drm` | `AVAILABLE` |
| E | `drm_clients_info` sin columna `tgid`; o `:272` describiendo al proceso original | `AVAILABLE` |
| F | dos `drm_file` del mismo dispositivo con `drm-pdev` distinto | `AVAILABLE` |
| B | `drm-pdev` no-BDF | `AVAILABLE` |
| C | `read_text` en la ruta de fdinfo | `AVAILABLE` (ejecutado: detectado) |
| **G** | `pasid` junto a PID sin fault concurrente | `NOT_AVAILABLE` → **`PROVISIONAL`** |
| **H** | fuente que haga de la VM identidad de proceso | `NOT_AVAILABLE` → **`PROVISIONAL`** |
| **N** | fuente que haga del GEM identidad de proceso | `NOT_AVAILABLE` → **`PROVISIONAL`** |
| I | clave de memoria por proceso | `AVAILABLE` |
| J | `drm-engine-*` por proceso, o monótona | `AVAILABLE` |
| L | mundo con 2 FD / 1 `drm_file` | `AVAILABLE` |
| M | master transferido sin `lessor` | `AVAILABLE` |
| A | symlink a nodo ausente/roto/otro BDF | `AVAILABLE` |

## 10 · OPEN_QUESTIONS

`U-1`…`U-11` normativas. Técnicas y **cerradas como indeterminadas**, sin reinvestigar:
fuente de amdgpu (G, H) · `drm_client_debugfs.c` · sitio de reasignación de `drm_file.pid` ·
minor `ACCEL` en el universo de nodos. `drm-client-id` en `VALUE = NOT_AVAILABLE`.

## 11 · SEPARACIÓN DE CAPAS — conservadas sin colapsar

| | N-1 | N-2 | N-3 | N-4 | N-5 | N-7 | N-9 | N-10 |
|---|---|---|---|---|---|---|---|---|
| ¿el sistema lo expone? | sí | sí | sí | sí | sí (debugfs) | **no** | **no** | n/a |
| ¿el analizador pudo leerlo? | sí | sí | sí | presencia sí, **valor no** | no implementado | no | no | n/a |
| ¿lo observamos? | sí | sí (`PROVEN`) | sí | solo por cita | no | no | no | `OWNERSHIP=UNKNOWN` |
| ¿demuestra la propiedad? | parcial | sí | sí | **no** (sin valor) | no | no | no | no |
| ¿satisface un requisito? | **`UNKNOWN`** | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `NO` | `NO` | `NO` | defectuoso |

`EMPTY_UNIVERSE ≠ ALL_OBSERVED_OBJECTS_SATISFY_PROPERTY` — protegido por guard y por test.
`ABSENCE_OF_DATA ≠ EVIDENCE_OF_ABSENCE` — `NOT_AVAILABLE` nunca se convirtió en ausencia.

## 12 · CODE_CHANGE_REQUIRED

**NO**, con una excepción aislada y **no ejecutada**: renombrar `card_clients` → `card_drm_client_id_fds`
y `render_clients` → `render_drm_client_id_fds` (líneas 2965-2966), porque el nombre afirma
`clients` y el valor es un conteo de FDs. `CODE_CHANGE_NEEDED = YES` para ese ítem; requiere
autorización y actualización de los consumidores del artefacto.

## 13 · PROJECT_MAPPING

**`NOT_ATTEMPTED`**. Ninguna de las 14 propiedades tiene obligatoriedad asignada.
`ANY_ALL = NOT_DECIDED` · `PASS_FAIL = NOT_DEFINED` · `TECHNICAL_MODEL = CLOSED`.

```
DECOMPOSED_PROPERTIES = 14   (A..N)
DEFS_ESTABLISHED      = 10   (A,B,C,D,E,F,I,J,L,M)  +  N parcial
SOURCE_INCOMPLETE     = 2    (G, H)
AMBIGUOUS             = 0
PROVISIONAL           = 3    (G, H, N) — sin falsador disponible
CODE_CHANGE_REQUIRED  = NO   (salvo renombrado de 2 claves, NO ejecutado)
```
