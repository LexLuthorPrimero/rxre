# R1-SEMANTIC-DECOMPOSITION-20260926

`DOCUMENT_KIND` = `SEMANTIC_DECOMPOSITION` · **READ_ONLY**
Reutiliza la evidencia de `R1-TECHNICAL-MODEL-CLOSURE-20260926.md` (`ee86a3a7…`) y de
`R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md` (`736ad20a…`). No re-deriva nada.
`PROJECT_MAPPING` = **`NOT_ATTEMPTED`** · `IMPLEMENTATION_AUTHORIZED` = **`NO`**
Kernel de referencia: **linux v6.12**.

## 1 · `ORIGINAL_HUMAN_PHRASE`

> `AGENTS.md:176-177` — "`FULL` requires complete attributable evidence for the RX550's card and
> render nodes, identified by PCI identity rather than by node name"
> `AGENTS.md:180-181` — "If FD visibility is incomplete, a permission is denied, root namespaces
> are not covered, **a client is active** or a writer is unresolved, then `OWNERSHIP != FULL`"

Dos sintagmas, **ambos mezclados**: `attributable` y `client`.

## 2 · `WHY_SEMANTICALLY_MIXED`

| Sintagma | Mezcla | Por qué no es una unidad |
|---|---|---|
| `attributable` | ocho conceptos | cuatro con **fuentes distintas** (`/proc`, sysfs, `fdinfo`, `fdinfo`); cuatro **ni siquiera son del mismo dominio** (cliente DRM, dirección PCI, VM/PASID, page-fault) |
| `client` | al menos tres | `drm_file` (core, spec), `drm_master` (ownership de nodos primarios), page-fault `client-id` (amdgpu). **El mismo nombre, tres entidades** |

**`a client is active` no se usa como especificación.** Es parte del mismo defecto: combina un
sustantivo ambiguo (`client`) con un predicado temporal (`active`) sin unidad declarada. **No se
infiere de ella ninguna obligación**, y no se diseña ningún contador a partir de ella.

## 3 · `DECOMPOSED_PROPERTIES`

| # | `PROPERTY_NAME` | `TARGET_ENTITY` | `UNIT` | `SOURCE` | `RELATION` |
|---|---|---|---|---|---|
| P-1 | `DRM_FD_ENUMERATION` | FD DRM | **FD** | symlink `/proc/<pid>/fd/<n>` | FD → nodo |
| P-2 | `DRM_FDINFO_READABILITY` | FD DRM | **FD** | `/proc/<pid>/fdinfo/<n>` no vacío | FD → texto |
| P-3 | `DRM_NODE_COMPLETENESS` | universo de FDs | descriptor / proceso | los 4 términos de visibilidad | proceso → tabla de FDs |
| P-4 | `DRM_DEVICE_IDENTITY` (**S-3**) | `drm_minor`/`drm_device` | nodo (dispositivo) | sysfs; `minor->dev`; `dev_is_pci` | minor → drm_device → PCI |
| P-5 | `DRM_CLIENT_ID_PRESENCE` | clave `drm-client-id` | **FD** | `drm_file.c:942-943` | FD → clave |
| P-6 | `DRM_PCI_ADDRESS_PRESENCE` | clave `drm-pdev` | **FD** | `drm_show_fdinfo` | FD → clave (dispositivo). **NO es S-3**: unidad `FD`, no dispositivo |
| P-7 | `DRM_PASID_PRESENCE` | clave `pasid` | **FD** | **sin fuente en el core v6.12 ni en la spec**; convención de driver | FD → clave (vmid) |
| P-8 | `DRM_FILE_IDENTITY` (**S-1**) | `struct drm_file` | **`drm_file`** | `drm_file.c:142`; spec `:64-72` | drm_file → `client_id` |
| P-9 | `DRM_FILE_PROCESS_ASSOCIATION` | `struct drm_file` | `drm_file` | `drm_file.c:143` | drm_file → `struct pid` |
| P-10 | `DRM_FD_PROCESS_ASSOCIATION` | FD | **FD** | `/proc/<pid>/fd/<n>` | proceso → FD (posesión) |
| P-11 | `DRM_MEMORY_ACCOUNTING` | `drm_file` | agregado | `drm_print_memory_stats`; spec `:143-172` | drm_file → bytes por región |
| P-12 | `DRM_ENGINE_ACCOUNTING` | `drm_file` | `drm_file` × engine | spec `:79-133` | drm_file → ns/engine |
| P-13 | `DRM_MASTER_RELATION` | `drm_master` | un master | `drm_lease.h`; `drm_lease.c` | drm_file ↔ master, **transferible** |
| P-14 | `VM_PASID_PROCESS_RELATION` | vmid | vmid | docs amdgpu | vmid ↔ proceso, **episódica** |
| P-15 | `GPU_PAGE_FAULT_CLIENT_ID` | bloque del motor | bloque | — | — |
| P-16 | `DRM_FILE_DEBUGFS_CLIENT_ENTRY` (**S-4**) | fila de `drm_clients_info` | **`drm_file`** (1 fila : 1) | `drm_debugfs.c:73-113`, `:143` | `dev->filelist` → `drm_file` |
| P-17 | `DRM_CLIENT_DEBUGFS_FACILITY` (**S-5**) | facilidad de driver | `drm_file` | **`SOURCE_INCOMPLETE`** | `SOURCE_NOT_LOCATED` |

**P-16 es nueva y su hallazgo es material**, con tres afirmaciones separadas:

| # | Afirmación | Fuente | `CLASS` |
|---|---|---|---|
| a | `struct drm_file` **no tiene** miembro `debugfs_client` | `drm_file.h:164-391` leído **completo**; es la **única** definición de `struct drm_file {` en el conjunto leído (`grep` → 1) | `ABSENT_FROM_DEFINITION` |
| b | `drm_file.c` **no contiene** código de debugfs per-client | `drm_file.c` 996 L leído **completo**; 0 ocurrencias de `clients`, 0 de `debugfs_create` | `ABSENT_FROM_FILE` |
| c | el path `debugfs/dri/<minor>/clients` que el collector lee (`privileged_read_collector.py:719-722`) no está documentado ni creado por ninguna fuente del conjunto leído | `drm-usage-stats.rst` (0 menciones de `debugfs`), `drm_file.c`, `drm_drv.h`, `drm_internal.h` | `SOURCE_UNLOCATED` |

`drm_debugfs.c` y el resto de `drivers/gpu/drm/` **no fueron leídos**: que exista una facilidad
per-client *fuera* de `drm_file` es `NOT_READ`, **no** refutado. Lo establecido es (a) y (b), y que
el path concreto que consume el proyecto **no tiene fuente primaria localizada** — es
`AGENT_FORMALIZATION` + observación de host, no una garantía del core.

## 4 · `TECHNICAL_DEFINITIONS`

| | P-5 `DRM_CLIENT_ID_PRESENCE` | P-6 `DRM_PCI_ADDRESS_PRESENCE` | P-7 `DRM_PASID_PRESENCE` |
|---|---|---|---|
| `IDENTITY_SEMANTICS` | presencia de una clave | presencia de una clave | presencia de una clave |
| `LIFETIME` | la del FD | derivada al imprimir | la del FD |
| `MUTABILITY` | ninguna (texto) | ninguna (derivada) | ninguna (texto) |
| `OBSERVABILITY` | `EXPOSED` por el core, incondicional | `EXPOSED` **ssi** el dispositivo es PCI | `EXPOSED` por el driver |
| `WHAT_IT_PROVES` | que el texto traía la clave | que el texto nombra un **BDF** | que el texto traía un **vmid** |
| `WHAT_IT_DOES_NOT_PROVE` | identidad, nº de clientes, proceso | identidad de cliente; no transporta vendor/device/class | PID, proceso, ni relación con `drm_file` |
| `FALSIFIER` | dos `drm_file` con la misma clave | dos `drm_file` del mismo dispositivo con `drm-pdev` distinto | `PASID` impreso con PID sin fault concurrente |
| `PROVENANCE` | `PRIMARY_KERNEL_SOURCE` `drm_file.c:943`; `EXTERNAL_SPEC` `:64-72` | `PRIMARY_KERNEL_SOURCE` `drm_file.c:948-950`; `EXTERNAL_SPEC` `:59-62` | `SOURCE_INCOMPLETE`: 0 en `drm_file.c`, 0 en la spec |

| | P-8 `DRM_FILE_IDENTITY` (S-1) | P-9 `DRM_FILE_PROCESS_ASSOCIATION` (S-2) | P-10 `DRM_FD_PROCESS_ASSOCIATION` |
|---|---|---|---|
| `IDENTITY_SEMANTICS` | 1:1 con `drm_file` | el proceso que **usa** el archivo | el proceso que **posee** el FD |
| `LIFETIME` | la del `drm_file` | por instancia | la del FD |
| `MUTABILITY` | **una sola escritura en todo el core** (`:142`); por tanto inmutable en el core. El campo es **público** (`drm_file.h:281-282`) y la spec **no** promete estabilidad. **Alcance de la unicidad**: el contador es `static` de módulo (`drm_file.c:132`) → el valor es único **dentro de la vida del módulo `drm` cargado**; una recarga del módulo lo reinicia | **mutable**, documentado en la fuente primaria: «Updates are guarded with `dev->filelist_mutex` and reference must be dropped after a RCU grace period» (`drm_file.h:275-277`); updater `drm_file.c:435`; **sitio de llamada `SOURCE_NOT_LOCATED`** en el conjunto leído | re-evaluable |
| `OBSERVABILITY` | requiere `VALUE`: **no implementado** | **`EXPOSED`**, en dos carriers distintos: (a) por fdinfo **no**; (b) por el **core**, en `debugfs/dri/<minor>/clients`, **una fila por `drm_file`** con columna `tgid` (`drm_debugfs.c:92`, `:98-103`, `:143`) | `EXPOSED` vía la ruta |
| `WHAT_IT_PROVES` | nada todavía: solo hay `PRESENCE` | por el carrier (b): que existe una asociación observable entre ese `drm_file` y un **TGID** | qué proceso tenía ese descriptor |
| `WHAT_IT_DOES_NOT_PROVE` | que el count de FDs sea el de clientes | que sea la identidad **histórica** del proceso que abrió el FD: la fuente lo define «Process that is **using** this file» (`drm_file.h:272`) y `drm_auth.c:236-238` lo compara con `task_tgid(current)`, o sea que **se espera que siga al usuario actual** | que refleje el campo del núcleo; no distingue dos FDs de un `drm_file` |
| `FALSIFIER` | dos `drm_file` con la misma clave | `drm_clients_info` **sin** columna `tgid`, o `drm_file.h:272` describiendo al proceso **original**; alternativamente `drm_file_update_pid` inoperante | una ruta resuelta a otro proceso |
| `PROVENANCE` | `PRIMARY_KERNEL_SOURCE` `drm_file.c:142` + `drm_file.h:281-282`; `EXTERNAL_SPEC` `:66-68` (*"Conceptually the value should map 1:1 to the in kernel representation of `struct drm_file`"*) | `PRIMARY_KERNEL_SOURCE` `drm_file.c:143` (`task_tgid(current)`), `drm_file.h:271-278`, `drm_auth.c:233-244`, `drm_debugfs.c:92,98-103`. **`CORRECTED` 2026-09-26** por `X-1` | `INFERENCE` sobre la ruta `/proc` + `PRIMARY_KERNEL_SOURCE` `drm_file.h:437` |

| | P-11 `DRM_MEMORY_ACCOUNTING` | P-12 `DRM_ENGINE_ACCOUNTING` | P-13 `DRM_MASTER_RELATION` |
|---|---|---|---|
| `IDENTITY_SEMANTICS` | agregado por `drm_file` | `drm_file` × engine | un master |
| `LIFETIME` | derivada | contador del driver | `kref` |
| `MUTABILITY` | con `object_idr` | **no monótona** | **transferible** por leasing |
| `OBSERVABILITY` | **por driver**; `NOT_OBSERVED` aquí | **por driver**; `NOT_OBSERVED` aquí | por ioctl, **no** por fdinfo |
| `WHAT_IT_PROVES` | consumo agregado de ese `drm_file` por región | `>0` ⇒ trabajo de ese cliente; tiempo acumulado | qué `drm_file` posee el master |
| `WHAT_IT_DOES_NOT_PROVE` | no es inventario de objetos; `=0` no prueba no-uso; no es del PID | no es instantánea; `=0` no prueba no-uso; no es del proceso | **no** es identidad de cliente ni de proceso |
| `FALSIFIER` | clave de memoria por proceso en la spec | `drm-engine-*` por proceso, o declarada monótona | master transferido sin `lessor` |
| `PROVENANCE` | `PRIMARY_KERNEL_SOURCE` `drm_file.c:828-840`; `EXTERNAL_SPEC` `:140-175` | `EXTERNAL_SPEC` `:79-137` (`:86` *"belonging to this client"*, `:88-89` no monótona) | `PRIMARY_KERNEL_SOURCE` `drm_lease.h`; `drm_lease.c` |

`P-14` y `P-16`: `SOURCE_INCOMPLETE`. `P-15`: `SOURCE_INCOMPLETE`.

## 5 · `PROJECT_MAPPING`

**`NOT_ATTEMPTED`.**

Ninguna de P-1…P-16 tiene, hoy, un requisito humano explícito que la exija.
**Las dieciséis son `TECHNICAL_PROPERTY_WITHOUT_PROJECT_MAPPING`.** Ninguna se convierte en
obligación, y ninguna se combina.

| Propiedad | `TECHNICAL_PROPERTY_WITHOUT_PROJECT_MAPPING` | Evidencia |
|---|---|---|
| P-1, P-2, P-3, P-4 | sí | el texto nombra "complete" y "PCI identity"; **no** nombra cliente, PASID ni engine |
| P-5…P-12, P-16 | sí | ninguna frase del texto las nombra |
| P-13, P-14, P-15 | sí | ninguna; y `client` es ambiguo en las tres |

## 6 · `UNRESOLVED_ITEMS`

| | `CLASS` |
|---|---|
| clave de deduplicación de `drm-client-id` (global vs por dispositivo) | `CONFLICT_UNRESOLVED` (`C-4`) |
| page-fault `client-id` = `drm-client-id` | `CONFLICT_UNRESOLVED` (`C-1`) |
| sentidos de `client` | `CONFLICT_UNRESOLVED` (`C-2`) |
| `VM`, `PASID`↔`drm_file`, `driver_priv` amdgpu | `SOURCE_INCOMPLETE` |
| `P-15` `GPU_PAGE_FAULT_CLIENT_ID` | `SOURCE_INCOMPLETE` |
| `P-16` `DRM_CLIENT_DEV` — **no existe en el core v6.12** | `SOURCE_INCOMPLETE` · **hallazgo nuevo** |
| `P-8` requiere `VALUE`, que nada extrae | `REQUIERE_DEFINICIÓN` |
| `engine`/`memory` en este host | `NOT_OBSERVED` |

## 7 · `PROHIBITED_INFERENCES`

`FD count → client count` · `drm-client-id → proceso` · `drm-client-id → actividad` ·
`PASID → cliente DRM` · `drm-pdev → identidad de cliente` · `engine activity → proceso` ·
`GEM object → proceso` · `drm-master → drm-client-id` · `drm_client_dev → propiedad del core` ·
`any()`/`all()` entre dominios antes de tener definición normativa propia.

`"a client is active"` **no autoriza** ninguna de estas, ni ninguna otra: es parte de la frase
retirada.

## 8 · `FALSIFIERS`

Los 12 falsificadores de `R1-TECHNICAL-MODEL-CLOSURE` §10 siguen vigentes para P-1…P-13, P-15, P-16.
Verificados por ejecución en la implementación: 4 mutaciones del consumidor **detectadas**
(cláusula cruzada, `pasid`→`max()`, `STATE` exige presencia, acumulación de `scan_fds` colapsada) y
1 premisa propia **refutada** por no detección. Suite **308 OK**.

## 9 · `DECISION` (ronda 1)

```
HUMAN_REQUIREMENT_RETIRED_AS_MIXED_TERM = YES
TECHNICAL_PROPERTIES_SEPARATED           = YES   (16 propiedades, P-1..P-16)
NO_IMPLEMENTATION_AUTHORIZED              = YES
PROJECT_MAPPING                           = NOT_ATTEMPTED
```

## 10 · `RETIRED_TERMS` (única sección donde esos términos pueden aparecer)

| Término retirado | Tipo | Por qué se eliminó | Sustituto |
|---|---|---|---|
| `attributable` | `HUMAN_REQUIREMENT` | ocho conceptos, cuatro fuentes, cuatro dominios ajenos | P-1…P-10 |
| `complete` | `HUMAN_REQUIREMENT` | mezcla cobertura (P-3), contenido (P-2), legibilidad, identidad, asociación y accounting | P-2, P-3, y las demás por nombre |
| `client` | ambiguo | mismo nombre, **tres** entidades: `drm_file` (E-3), `drm_master` (E-10), page-fault `client-id` (E-17) | P-8 / P-13 / P-15 |
| `a client is active` | `HUMAN_REQUIREMENT` | sustantivo ambiguo + predicado temporal sin unidad declarada | **ninguno** — no autoriza nada |
| `PCI identity` | correcto, mal mezclado | confundido con identidad de cliente | P-4 (nodo) vs P-6 (clave fdinfo) |
| `DRM_ATTRIBUTION_FIELDS` | `AGENT_FORMALIZATION` | agregador que remezclaba dominios | *ninguno* — no recrear |
| `card_attributable`, `render_attributable`, `node_attributable` | `AGENT_FORMALIZATION` | predicados compuestos sobre el término retirado | cobertura (`node_coverage_complete`) + P-2, P-5, P-6, P-7 |
| `clients_pasid_attributable` | `AGENT_FORMALIZATION` | sin antecedente en `AGENTS.md`; unía `client` y `PASID` | retirado de 4 superficies |

**`client` no se elimina del vocabulario técnico**: `drm_file`, `drm_master`, `drm-client-id` y
`GPU page-fault client-id` son **cuatro** entidades y solo la cuarta está `SOURCE_INCOMPLETE`.
`PRIMARY_KERNEL_SOURCE` para las tres primeras: `drm_file.h:164-391`, `drm_lease.h`,
`drm_file.c:942-943`.

## 11 · `VERIFICATION_PASS_2` (P-1…P-16 contra las fuentes primarias)

Reverificación con líneas exactas sobre el conjunto leído. Sin re-derivación semántica.

| | Afirmación verificada | Fuente primaria | `CLASS` |
|---|---|---|---|
| 1 | `client_id` se asigna con un `atomic64` de módulo, una vez, en la alloc | `drm_file.c:142` | `OBSERVED` |
| 2 | `pid` = `task_tgid(current)`, es decir **TGID** | `drm_file.c:143` | `OBSERVED` |
| 3 | `drm-client-id` se imprime en `:943`; `drm-pdev` en `:948-950`, **solo si** `dev_is_pci` | `drm_file.c:942-950` | `OBSERVED` |
| 4 | **`drm_show_fdinfo` imprime exactamente 3 claves**: `drm-driver`, `drm-client-id`, `drm-pdev` | `drm_file.c:936-950` | `OBSERVED` |
| 5 | por tanto **`pasid` no lo imprime el core** y la spec **no lo define** (0 coincidencias) | `drm_file.c`; `drm-usage-stats.rst` | `SOURCE_INCOMPLETE` (P-7) |
| 6 | 1:1 conceptual con `struct drm_file`; unicidad **global o por dispositivo**, y en el segundo caso `drm-pdev` presente | spec `:64-72` | `EXTERNAL_SPEC` |
| 7 | `drm-pdev` = **dirección del slot PCI** del dispositivo | spec `:59-62`; `drm_file.c:948-950` | `OBSERVED`+`EXTERNAL_SPEC` |
| 8 | engine = tiempo **ejecutando workloads de este cliente**; **no monótona** | spec `:79-89` (`:86`, `:88-89`) | `EXTERNAL_SPEC` |
| 9 | memoria: clave base `drm-memory-<region>` **existe**; el core emite `drm-<stat>-<region>` | spec `:143`; `drm_file.c:840` | `OBSERVED` — la afirmación del doc de cierre era **correcta** |
| 10 | `drm-shared` = compartido con otro fichero, *"more than a single handle"* | spec `:155-158` | `EXTERNAL_SPEC` |
| 11 | `drm_file.pid` es *"Process that is using this file"* → **no** identidad histórica | `drm_file.h:272,279` | `PRIMARY_KERNEL_SOURCE` |
| 12 | `client_id` es un campo **público** del struct | `drm_file.h:281-282` | `PRIMARY_KERNEL_SOURCE` |
| 13 | `struct drm_file` y `struct drm_memory_stats` están definidos **una sola vez** en el conjunto leído | `drm_file.h:164`, `:475` | `OBSERVED` |

**Auditorías de capa**:
- `any(`/`all(` en este documento: **1** aparición, y es una **prohibición** (§7). Ninguna decisión.
  En `R1-TECHNICAL-MODEL-CLOSURE`: **0**. En `R1-REPAIRED-TECHNICAL-REQUIREMENTS`: 8/5, y **todas**
  son exclusiones explícitas (`:71`, `:326`, `:369`, `:406`, `:478`, `:484`, `:497`, `:507`).
- Ninguna fila P-1…P-16 afirma qué exige `OWNERSHIP`. Las únicas menciones de `OWNERSHIP` en el
  documento son la cita de `AGENTS.md` (§1) y el nombre de P-13, **renombrado** en esta ronda (§12).
- Los términos retirados no aparecen en §3 ni en §4. `complete` solo dentro del nombre de P-3.

## 12 · `CORRECTIONS` (esta ronda)

| # | Afirmación previa | Estado | Evidencia que la corrige |
|---|---|---|---|
| C-1 | P-7 `SOURCE` = `drm_show_fdinfo` | `REFUTED` | `drm_show_fdinfo` emite 3 claves, `pasid` **no** entre ellas (`drm_file.c:936-950`); 0 en la spec |
| C-2 | «el core v6.12 no tiene debugfs de clientes» / «convención de amdgpu» | `REFUTED` — la conclusión además es **falsa** | `drm_debugfs.c:143` registra `clients` en la lista del **core**; §16 |
| C-3 | `DRM_MASTER_OWNERSHIP` | `RENAMED` → `DRM_MASTER_RELATION` | colisionaba con el veredicto normativo `OWNERSHIP=FULL`; un `AGENT_FORMALIZATION` no puede reutilizar el token del requisito |
| C-4 | «`drm-memory-<region>` no existe en la spec» (hipótesis mía de esta ronda) | `REFUTED` | `drm-usage-stats.rst:143` — **existe**. La frase del doc de cierre era correcta. **No se corrigió nada** |
| C-5 | C-2 (`CONFLICT_UNRESOLVED`) citaba `drm-usage-stats.rst:68` como evidencia de *«this client»* | `CITATION_CORRECTED` | «this client» está en `:86` y `:150`, no en `:68`. La conclusión no cambia; la cita sí. Afecta a documentos `SUPERSEDED` (§13) |
| **C-7** | `drm_client_dev` nombrado como entidad de kernel en la tabla de `CLIENT` de `R1-TECHNICAL-SEPARATION-TABLE-20260926.md` | **`PROVENANCE_ERROR` CORREGIDO** | `drm_client_dev` **no existe** como símbolo en el conjunto primario. Único match: `drm_client_dev_restore(dev)` en `drm_file.c:391`, llamado desde `drm_lastclose()` (`:389`); **definición fuera del conjunto leído** → `SOURCE_NOT_LOCATED`. El token es `HUMAN_REQUIREMENT`, no semántica de kernel |
| **C-8** | «`client_id` inmutable en el core» sin alcance de unicidad | `SCOPE_PRECISION_ADDED` | `drm_file.c:132` `static atomic64_t ident = ATOMIC_INIT(0);` es de **ámbito de módulo**, y hay **una sola escritura** (`:142`). La unicidad del valor es **dentro de la vida del módulo `drm` cargado**; una recarga lo reinicia |
| **C-9** | el modelo documentaba `drm_minor` sin mencionar el tipo `ACCEL` | `OMISSION_CORRECTED` | `enum drm_minor_type` tiene **cuatro** valores ABI — `PRIMARY=0`, `CONTROL=1`, `RENDER=2`, `ACCEL=32` — y `drm_file.h:58-60` advierte que son ABI porque determinan la numeración `/dev/dri/renderD*`. `drm_is_accel_client()` (`drm_file.h:432`) es una función del **core** que usa «client» para un *file abierto sobre un minor accel*: **quinta** entidad que el core llama «client». El alcance de P-3 **no** se redefine: `PROJECT_MAPPING = NOT_ATTEMPTED` |

## 13 · `CROSS_DOCUMENT_INCONSISTENCY` (no se corrige aquí)

| Documento | `PROJECT_MAPPING` declarado | Nota |
|---|---|---|
| `R1-TECHNICAL-MODEL-CLOSURE-20260926.md` | `NOT_ATTEMPTED` | vigente |
| `R1-SEMANTIC-DECOMPOSITION-20260926.md` (este) | `NOT_ATTEMPTED` | vigente |
| `R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md:7` | `DEFERRED_PENDING_SPEC_CLOSURE` | vigente, `NORMATIVE_STATUS = RESEARCH_ONLY` |

Ambos tokens significan «sin mapeo decidido», pero **no son el mismo token** y los documentos no
coinciden. `REFERENCE_STATUS=INCONSISTENT`. **No se edita** el documento con estado normativo: su
§5 ya excluye explícitamente `any()`/`all()`, qué exige `OWNERSHIP` y los `PASS`/`FAIL`. Su
resolución requiere autorización aparte.

La cita errónea de C-2 (C-5) permanece en `R1-TECHNICAL-SEMANTIC-MODEL-v3-20260926.md:464`,
`R1-TECHNICAL-SEMANTIC-MODEL-v3-20260926.md:259` y `R1-TECHNICAL-SEMANTIC-MODEL-v2-20260926.md:421`.
Los tres están `SUPERSEDED`/`HISTORICAL`: **no se reescriben**, se registran aquí como
`HISTORICAL_CITATION_ERROR`.

## 14 · `OPEN` (no reabre el modelo técnico)

| | `CLASS` | Por qué no bloquea `TECHNICAL_MODEL` |
|---|---|---|
| No existe especificación normativa que seleccione P-1…P-16 | `REQUIREMENT_UNRESOLVED` | el modelo técnico está cerrado y separado; la ausencia de mapeo **no lo reabre** |
| unicidad de `drm-client-id`: global o por dispositivo | `CONFLICT_UNRESOLVED` (`C-4`) | la spec **admite ambas**; ambas están documentadas, ninguna elegida |
| sentidos de `client` (`C-1`, `C-2`) | `CONFLICT_UNRESOLVED` | las cuatro entidades están separadas por nombre y fuente |
| `VM`, `PASID`↔`drm_file`, `driver_priv` amdgpu, P-7, P-15, P-16 | `SOURCE_INCOMPLETE` | registrado con la fuente que **sí** se leyó; no se rellena el hueco |
| `drm_debugfs.c` y el resto de `drivers/gpu/drm/` | `NOT_READ` | delimita (a)/(b) sin convertirlas en refutación del core |
| `engine`/`memory` en este host | `NOT_OBSERVED` | la spec sí está disponible; la propiedad se define igual |
| P-8 requiere `VALUE` | `REQUIERE_DEFINICIÓN` | irrelevante mientras `PROJECT_MAPPING = NOT_ATTEMPTED` |
| `PROJECT_MAPPING` con dos tokens (§13) | `INCONSISTENT` | ambos significan «no decidido»; requiere autorización |
| `fdinfo_attribution` sin llamadas en producción | `LIMITATION` | sin efecto en ninguna conclusión |

**`REQUIREMENT_INTENT_RECONSTRUCTION` = `NOT_ATTEMPTED`** y no se intentará.

## 15 · `DECISION` (final)

```
TECHNICAL_MODEL                      = CLOSED
PROJECT_MAPPING                      = NOT_ATTEMPTED
HUMAN_MIXED_TERM                     = RETIRED
REQUIREMENT_INTENT_RECONSTRUCTION    = NOT_ATTEMPTED
NORMATIVE_REQUIREMENT_REWRITE        = OPEN  (REQUIREMENT_UNRESOLVED, humano)
IMPLEMENTATION_AUTHORIZED            = NO
TECHNICAL_PROPERTIES_SEPARATED       = YES  (16, P-1..P-16, ninguna depende de `attributable`)
```

# 16 · `P16_RESOLUTION` — lectura de `drm_debugfs.c` (único fichero autorizado)

`drm_debugfs.c` **linux v6.12**, `raw.githubusercontent.com/torvalds/linux/v6.12/…`, HTTP 200,
21157 bytes, 16 ficheros en el conjunto (12 primarios + 2 artefactos 404 de amdgpu + 1 `.tmp`).
Ningún otro fichero leído. **Ampliar el conjunto de fuentes no está autorizado.**

## 16.1 · Resuestas a las tres preguntas

| Pregunta | Respuesta | `CLASS` |
|---|---|---|
| ¿El core DRM crea/genera `debugfs/dri/<minor>/clients`? | **Sí**, y por ruta de symlink, no literalmente ese path | `SOURCE_LOCATED` |
| ¿Qué entidad representa ese recurso? | **Una fila por `struct drm_file`** de `dev->filelist` | `OBSERVED` |
| ¿Qué relación tiene con `struct drm_file`? | **directa, 1 fila : 1 `drm_file`**; `priv` **es** `struct drm_file *` | `OBSERVED` |
| ¿Su existencia/nombre está garantizada por el core? | **Sí, incondicionalmente**, en `dev->debugfs_root`; sin filtro de features | `OBSERVED` |

## 16.2 · Cadena de creación, con línea

| # | Paso | Fuente |
|---|---|---|
| 1 | `{"clients", drm_clients_info, 0}` en la lista del **core** | `drm_debugfs.c:143` (`drm_debugfs_list[]` en `:141-145`) |
| 2 | `drm_debugfs_dev_register()` añade los 3 de esa lista a `dev->debugfs_root` | `drm_debugfs.c:307-309` |
| 3 | ese add **no filtra por features** — el filtro vive en `drm_debugfs_create_files`, para listas del driver | `drm_debugfs.c:354-370` vs `:239-263` |
| 4 | `dev->debugfs_root = debugfs_create_dir(dev->unique, root)` | `drm_debugfs.c:290-292` |
| 5 | `drm_debugfs_register()` crea `debugfs/dri/<minor_id>` como **symlink** a `dev->unique` | `drm_debugfs.c:319-327` |
| 6 | `minor->debugfs_root = dev->debugfs_root` → card y render apuntan al mismo directorio | `drm_debugfs.c:330` |
| 7 | el collector resuelve `debug_root/dri/<minor>` y lee `…/"clients"` | `privileged_read_collector.py:688`, `:719-722` |

**Consecuencia 1**: `debugfs/dri/<minor>/clients` **no** es un path literal del core; es el symlink
del paso 5. `P-16` no debe llamarse «el directorio per-client»: es un **fichero de texto**.

**Consecuencia 2**: el mismo fichero es el mismo para el minor de card y el de render (paso 6). Un
`clients` por minor **no** son dos poblaciones distintas.

## 16.3 · Contenido exacto y qué demuestra

Cabecera (`drm_debugfs.c:80-86`): `command  tgid  dev  master  a  uid  magic`.

| Columna | Origen | Entidad |
|---|---|---|
| `command` | `task->comm` (`:102`) | proceso |
| `tgid` | `pid_vnr(pid)`, con `pid = rcu_dereference(priv->pid)` (`:98`, `:103`) | **TGID del `drm_file`** |
| `dev` | `priv->minor->index` (`:104`) | **`drm_minor`**, no BDF |
| `master` | `drm_is_current_master(priv)` (`:92`, `:105`) | `drm_master` (`drm_auth.c:81`) |
| `a` | `priv->authenticated` (`drm_file.h:174`) | `drm_file` |
| `uid` | `__task_cred(task)->euid` (`:100`) | credencial del proceso |
| `magic` | `priv->magic` (`:108`; `drm_file.h:285`) | token de autenticación del **`drm_file`** |

Orden: del `drm_file` **más antiguo** al más reciente (`list_for_each_entry_reverse` sobre
`dev->filelist`, `:92`; `lhead` en `drm_file.h:293`). `dev->filelist`/`filelist_mutex` en `drm_drv.h`.

**Lo que este recurso NO contiene**: `drm-client-id`. `magic` es `drm_magic_t`
(`drm_file.h:285`), no `u64 client_id` (`drm_file.h:282`), y `dev` es un **índice de minor**, no un
BDF. Por tanto **no puede** suplir el `VALUE` que P-8 necesita, ni unir `client_id` con un `tgid`, ni
identificar el dispositivo por PCI.

## 16.4 · Efecto sobre el modelo

`TECHNICAL_MODEL` sigue **`CLOSED`**. `P-1`…`P-15` **no cambian**: son propiedades de fdinfo, sysfs
o `/proc`, y este recurso es debugfs. Ninguna se convierte en requisito de proyecto.
`PROJECT_MAPPING` sigue **`NOT_ATTEMPTED`**; no se ha introducido ningún requisito, predicado,
`any()`/`all()` ni `PASS`/`FAIL`. `REQUIREMENT_INTENT_RECONSTRUCTION` sigue **`NOT_ATTEMPTED`**.

---

# 17 · `CORRECTIONS_APPLIED` — X-1, X-2, X-3 aplicadas (y C-6)

Instrucción aplicada: **corrección documental derivada de evidencia primaria**, autorizada en esta
ronda. `CORRECTION_CLASS` = `DOCUMENTARY_FROM_PRIMARY_SOURCE`, **no** `INFERENCE`, **no** normativa.

| # | Definición | Campo | Valor anterior | Lo que la fuente primaria exige | `STATUS` |
|---|---|---|---|---|---|
| X-1 | **P-9** `DRM_FILE_PROCESS_ASSOCIATION` (S-2) | `OBSERVABILITY` | **`NOT_EXPOSED`** («el campo no se publica») | **`REFUTED`**: el core publica el TGID de cada `drm_file` en `drm_debugfs.c:92`, `:98-103`, `:143` | **`APPLIED` 2026-09-26** |
| X-2 | **P-16** `DRM_CLIENT_DEV` | `TARGET_ENTITY`, `UNIT`, `RELATION`, `OBSERVABILITY` | «nodo por el que se abrió» / `drm_file` / «drm_file → nodo de apertura» / «driver-specific» | el recurso es un **fichero que lista todos los `drm_file` del dispositivo**, una fila por `drm_file`; la relación es *listing*, no *nodo de apertura*; `SOURCE_LOCATED` en el core | **`APPLIED` 2026-09-26** → P-16 = `DRM_FILE_DEBUGFS_CLIENT_ENTRY` (S-4) |
| X-3 | **P-16** nombre | — | `DRM_CLIENT_DEV` | nombra un «client dev» que la fuente no respalda | **`APPLIED` 2026-09-26**: nombre **retirado**; la facilidad de driver separada se registra como P-17 = `DRM_CLIENT_DEBUGFS_FACILITY` (S-5) |

**X-1 aplicada**: `OBSERVABILITY` de P-9 pasó de `NOT_EXPOSED` a `EXPOSED`, distinguiendo los dos
carriers: **fdinfo no lo publica** y **el core sí**, por `debugfs/dri/<minor>/clients`. Se
actualizaron además `MUTABILITY`, `WHAT_IT_PROVES`, `WHAT_IT_DOES_NOT_PROVE`, `FALSIFIER` y
`PROVENANCE`. **No** se tocó requisito humano, predicado del proyecto, `any()`/`all()`,
`PASS`/`FAIL`, `OWNERSHIP`, `card_node_complete`, `render_node_complete`, `drm_fds_enumerated`,
`DRM_ATTRIBUTION_FIELDS`, collector, tests ni `AGENTS.md`.

**X-2/X-3 aplicadas**: `DRM_CLIENT_DEV` **retirado** — el nombre afirmaba un «client dev» que la
fuente no sostiene. Lo sustituyen **dos** propiedades porque son **dos** recursos:
`DRM_FILE_DEBUGFS_CLIENT_ENTRY` (la fila del fichero `clients` del **core**, `SOURCE_LOCATED`) y
`DRM_CLIENT_DEBUGFS_FACILITY` (`drm_client_debugfs_init()`, `SOURCE_INCOMPLETE`). No se fusionan, no
se sustituyen, y **ninguna** se declara equivalente a `drm-client-id`.

**C-6 · precisión de la mutabilidad**: la afirmación previa «se reasigna salvo `was_master`»
(atribuida a `drm_auth.c:215-242`) **sobreafirmaba**. Verificado ahora: la mutabilidad está
documentada en la propia fuente primaria (`drm_file.h:275-277`); el updater es
`drm_file.c:435 drm_file_update_pid()`; y `drm_auth.c:233-244` (`drm_master_check_perm`) compara
`pid` con `task_tgid(current)`. El **sitio donde se reasigna** no está en el conjunto leído →
`SOURCE_NOT_LOCATED`. La sustancia —mutable, y **no** la identidad del proceso que abrió el FD—
**se mantiene**; lo que se corrige es la atribución de la evidencia.

**X-1 era la de mayor consecuencia** y queda aplicada: el cambio afecta a `OBSERVABILITY`,
`WHAT_IT_PROVES` y `WHAT_IT_DOES_NOT_PROVE` de P-9. **No** afecta a `PROHIBITED_INFERENCES`: unir
`drm_file` con un proceso por un carrier del core **no** autoriza a tratarlos como la misma entidad.
`drm_file.pid` es el proceso que *usa* el archivo; un proceso que *posee* un FD es P-10; ninguna de
las dos es `drm-client-id`.

**Ningún cambio aplicado.** Ningún fichero de código, test, `AGENTS.md`, `README.md` ni documento
histórico fue tocado.

## 18 · `RESIDUAL` — lo que sigue `SOURCE_INCOMPLETE`

`drm_debugfs.c:311-313`, dentro de `if (drm_core_check_feature(dev, DRIVER_MODESET))`:
`drm_framebuffer_debugfs_init(dev)` y **`drm_client_debugfs_init(dev)`**.

`drm_client_debugfs.c/.h` **no están** en el conjunto leído y **no están autorizados** para esta ronda.
Desde `drm_debugfs.c` **no** se puede determinar qué path crea. Queda abierto:

| # | Pregunta sin responder | Por qué no se infiere | `CLASS` |
|---|---|---|---|
| R-1 | ¿`drm_client_debugfs_init()` crea `…/clients/<algo>`? | requeriría leer `drm_client_debugfs.c` | `SOURCE_INCOMPLETE` |
| R-2 | Si lo hace, ¿**colisiona en nombre** con el **fichero** `clients` del core (paso 1)? | dos entradas con el mismo nombre en el mismo directorio; no se puede resolver sin R-1 | `SOURCE_INCOMPLETE` |
| R-3 | En caso de colisión, ¿qué lee realmente `read_text(clients, 65536)` — la tabla del core, un directorio (`EISDIR`), o nada? | depende de R-2 | `SOURCE_INCOMPLETE` |
| R-4 | ¿el contenido observado en este host fue la tabla del core? | `HOST_SCOPE` distinto; requiere ejecución, no autorizada | `UNKNOWN` |

R-2 es material: determina si la observación `client` que el proyecto ya tiene se apoya sobre el
**core** o sobre una convención. **No se decide aquí.** Cerrarlo requiere autorización para leer
**un** fichero: `drivers/gpu/drm/drm_client_debugfs.c` (linux v6.12).

---

# 19 · `SEPARATION_REGISTER` — S-1 … S-7

Siete separaciones independientes. Ninguna es requisito del proyecto. Los nombres son
`AGENT_FORMALIZATION`; su **semántica** procede de las fuentes primarias citadas fila por fila.

| | S-1 `DRM_FILE_IDENTITY` | S-2 `DRM_FILE_PROCESS_ASSOCIATION` |
|---|---|---|
| `PROPERTY_NAME` | S-1 (P-8) | S-2 (P-9) |
| `TARGET_ENTITY` | `struct drm_file` | `struct drm_file` |
| `UNIT` | un `drm_file` | un `drm_file` |
| `SOURCE` | `drm_file.c:142` (`atomic64_inc_return(&ident)`); contador `static atomic64_t ident` de **ámbito de módulo** (`drm_file.c:132`); campo `drm_file.h:281-282`; carrier fdinfo `drm_file.c:943` | `drm_file.c:143` (`task_tgid(current)`); campo `drm_file.h:271-278`; carrier debugfs `drm_debugfs.c:92,98-103` |
| `RELATION` | `drm_file` → `client_id`, **1:1** | `drm_file` → proceso que **usa** el archivo, 1:1 en el instante |
| `IDENTITY_SEMANTICS` | identificador **asociado al `drm_file`**, emitido por fdinfo; la spec lo dice 1:1 conceptual con `struct drm_file` (`:66-68`) | proceso que **está usando** ese file; **no** el que lo abrió originalmente |
| `LIFETIME` | la del `drm_file` | por instancia; cambia con el uso |
| `MUTABILITY` | inmutable en el core; el campo es **público** y la spec **no** promete estabilidad | **mutable**, documentado en `drm_file.h:275-277`; updater `drm_file.c:435`; sitio de llamada `SOURCE_NOT_LOCATED` |
| `OBSERVABILITY` | `PRESENCE` por fdinfo; **`VALUE` no implementada** | **`EXPOSED`** por el carrier debugfs; **no** por fdinfo |
| `WHAT_IT_PROVES` | que el texto traía la clave; y que el `drm_file` tiene un identificador | que hay una asociación observable `drm_file` ↔ TGID |
| `WHAT_IT_DOES_NOT_PROVE` | que sea PID · FD · proceso · `drm_master` · PASID · GPU page-fault `client-id`; ni el nº de clientes | que sea la identidad **histórica** del opener (`drm_auth.c:236-238` lo compara con `task_tgid(current)`) |
| `FALSIFIER` | dos `drm_file` con el mismo `client_id` | `drm_clients_info` sin columna `tgid`, o `drm_file.h:272` describiendo al proceso original |
| `PROVENANCE` | `PRIMARY_KERNEL_SOURCE` + `EXTERNAL_SPEC` | `PRIMARY_KERNEL_SOURCE`. `CORRECTED` 2026-09-26 (`X-1`) |

| | S-3 `DRM_DEVICE_IDENTITY` | S-4 `DRM_FILE_DEBUGFS_CLIENT_ENTRY` |
|---|---|---|
| `PROPERTY_NAME` | S-3 (P-4) | S-4 (P-16) |
| `TARGET_ENTITY` | `drm_device` / dispositivo PCI | **una fila** producida por `drm_clients_info` para un `struct drm_file` |
| `UNIT` | un dispositivo (nodo) | **`drm_file`** — una fila por elemento de `dev->filelist` |
| `SOURCE` | sysfs + `minor->dev` + `dev_is_pci`; `drm-pdev` en `drm_file.c:948-950`; spec `:59-62`; `enum drm_minor_type` con **cuatro** valores ABI `PRIMARY=0`, `CONTROL=1`, `RENDER=2`, **`ACCEL=32`** (`drm_file.h:58-66`, `:80`) | `drm_debugfs.c:73-113`; registrada en `drm_debugfs_list[]` en `:143`; creada en `dev->debugfs_root` (`:292`, `:307-309`); alcanzable como `debugfs/dri/<minor>/clients` por el symlink `:326` |
| `RELATION` | `drm_minor` → `drm_device` → PCI | `dev->filelist` → `drm_file`; **1 fila : 1 `drm_file`** |
| `IDENTITY_SEMANTICS` | **dirección PCI** (`domain:bus:slot.func`) del dispositivo | fila de texto con cabecera `command tgid dev master a uid magic` (`:80-86`) |
| `LIFETIME` | la del dispositivo | la del `drm_file` |
| `MUTABILITY` | inmutable | volátil: se imprime bajo `filelist_mutex` + `rcu_read_lock` (`:97,112`) |
| `OBSERVABILITY` | `EXPOSED` por sysfs; `drm-pdev` **ssi** `dev_is_pci` | `EXPOSED` **incondicionalmente** (`drm_debugfs_add_file` `:354-370` no filtra por features) |
| `WHAT_IT_PROVES` | que el nodo **es** el dispositivo, y su BDF | que existe un `drm_file` asociado a un **TGID**, y si es master actual, y su uid, y su `magic` |
| `WHAT_IT_DOES_NOT_PROVE` | que sea identidad de **cliente**; no transporta vendor/device/class; y el tipo de minor `ACCEL` es un **cuarto** tipo de nodo que la enumeración card/render del proyecto no cubre (alcance de P-3 **no** redefinido aquí: `PROJECT_MAPPING = NOT_ATTEMPTED`) | **NO contiene `drm-client-id`**: `magic` es `drm_magic_t` (`drm_file.h:285`), no `u64 client_id` (`:282`), y `dev` es `priv->minor->index`, **no** un BDF. No sustituye a S-1 |
| `FALSIFIER` | **(a)** `drm-pdev` emitiendo algo que no sea `domain:bus:slot.func` — refuta «dirección PCI»; **(b)** dos `drm_file` del mismo dispositivo con `drm-pdev` distinto — refuta «constante por dispositivo» | `client_id` o un BDF en la salida de `drm_clients_info`; una fila que no esté en `dev->filelist` |
| `PROVENANCE` | `PRIMARY_KERNEL_SOURCE` | `PRIMARY_KERNEL_SOURCE`. `CORRECTED` 2026-09-26 (`X-2`, `X-3`) |

| | S-5 `DRM_CLIENT_DEBUGFS_FACILITY` | S-6 `VM_PASID_PROCESS_RELATION` | S-7 `GPU_PAGE_FAULT_CLIENT_ID` |
|---|---|---|---|
| `PROPERTY_NAME` | S-5 (P-17) | S-6 (P-14) | S-7 (P-15) |
| `TARGET_ENTITY` | facilidad de debugfs de driver | vmid | bloque del motor |
| `UNIT` | `drm_file` (presumido, **no** verificado) | vmid | bloque |
| `SOURCE` | llamada en `drm_debugfs.c:311-313` bajo `DRIVER_MODESET`; **`drm_client_debugfs.c` NO LEÍDO** | docs de amdgpu | **`SOURCE_INCOMPLETE`** |
| `RELATION` | **`SOURCE_NOT_LOCATED`** | vmid ↔ proceso, **episódica** | — |
| `IDENTITY_SEMANTICS` | **`UNKNOWN`** | PASID = **vmid**; se relaciona con un proceso **solo durante un page fault y con el proceso activo** | identificador de un **bloque del motor**, no de un `drm_file` |
| `LIFETIME` | `UNKNOWN` | la del VM | la del bloque |
| `MUTABILITY` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `OBSERVABILITY` | `SOURCE_INCOMPLETE` | `SOURCE_INCOMPLETE`: 0 ocurrencias de `pasid` en la spec, 0 en el core v6.12; **convención de driver** | `NOT_AVAILABLE` |
| `WHAT_IT_PROVES` | nada todavía | nada en este host | nada todavía |
| `WHAT_IT_DOES_NOT_PROVE` | **no** se asume igual al fichero `clients` del core; **no** lo sustituye; **no** es equivalente a `drm-client-id` | **no** es `drm-client-id`, **no** es PID, **no** es identidad permanente de proceso | **no** es `drm-client-id`; la palabra «client» **no** es evidencia de equivalencia |
| `FALSIFIER` | el fichero `clients` del core y esta facilidad siendo **necesariamente el mismo** recurso → cerraría `SOURCE_INCOMPLETE` | `pasid` impreso con un PID sin fault concurrente | fuente primaria que ligue page-fault `client-id` y `drm-client-id` |
| `PROVENANCE` | `PRIMARY_KERNEL_SOURCE` (parcial) + `SOURCE_INCOMPLETE` | `SOURCE_INCOMPLETE` | `SOURCE_INCOMPLETE` |

**Prohibiciones que S-1…S-7 sostienen** (`PROHIBITED_INFERENCES`, §7): ninguna de las siete se
convierte en las otras seis. `DRM_FILE_DEBUGFS_CLIENT_ENTRY` **no** es un sustituto de
`DRM_FILE_IDENTITY`; `PASID` **no** es `drm-client-id`; `drm-pdev` **no** es identidad de cliente.
`PROJECT_MAPPING` sigue `NOT_ATTEMPTED`: **ninguna** de S-1…S-7 es un requisito.

# 20 · `EXCEPTIONS` — afirmaciones falsas que **no** se corrigen aquí

| # | Dónde | Por qué no se corrige |
|---|---|---|
| E-1 | `R1-20260926T030435Z.json` → `AGENTS_OWNERSHIP_MATRIX…EVIDENCE` = `"card1 / 8 attributable client(s)"` | **artefacto runtime preservado**: reescribirlo destruiría evidencia histórica. `HISTORICAL_NOMENCLATURE_DEFECT` |
| E-2 | `OWNERSHIP-AUDIT-HOST-C-20260925T231635Z.md:74-88`, `VFIO-FEASIBILITY-AUDIT-20260925T132242Z.md:188` | capturas y auditorías preservadas |
| E-3 | `privileged_read_collector.py:1569, 2816, 3301` («11-condition») y `:2345, 2439, 2907` («no DRM client») | **código**: no autorizado a modificar |
| E-4 | `R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md:7` (`DEFERRED_PENDING_SPEC_CLOSURE`) y `:225` | documento con `NORMATIVE_STATUS = RESEARCH_ONLY`: no autorizado |
| E-5 | `00-INDICE/PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md:197` | documento de protocolo vivo, fuera del alcance técnico-modelo |
| E-6 | `R1-TECHNICAL-SEMANTIC-MODEL-v2/v3:421, 259, 464` (cita errónea de C-2) | `HISTORICAL` / `SUPERSEDED`: no se reescriben |

**Ninguna de las seis es una afirmación del modelo técnico vigente.** Todas están fuera de los
documentos de modelo y registradas con su razón.

# 21 · `DECISION` (final, tras la corrección)

```
TECHNICAL_MODEL                   = CLOSED
DOCUMENTATION_DEFECT              = CLOSED   (P09 corregido; X-1/X-2/X-3 APPLIED;
                                               C-6 precisión de evidencia aplicada)
DOCUMENTATION_DEFECT_SCOPE        = TECHNICAL_MODEL_DOCUMENTS_ONLY
                                   (6 excepciones registradas en §20, ninguna corregible aquí)
PROJECT_MAPPING                   = NOT_ATTEMPTED
HUMAN_MIXED_TERM                  = RETIRED
REQUIREMENT_INTENT_RECONSTRUCTION = NOT_ATTEMPTED
NORMATIVE_REQUIREMENT_REWRITE     = OPEN  (REQUIREMENT_UNRESOLVED, humano)
TECHNICAL_PROPERTIES              = P-1..P-17 (S-1..S-7 canónicas), 17 propiedades,
                                     ninguna dependiente de `attributable`
IMPLEMENTATION_AUTHORIZED         = NO
CODE_OR_TEST_OR_AGENTS_CHANGES    = NONE
```
