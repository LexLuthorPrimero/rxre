# R1-ATTRIBUTION-DECOMPOSITION-MODEL-20260926

`DOCUMENT_KIND = RESEARCH` + `MODEL_DESIGN` · `NORMATIVE_STATUS = RESEARCH_ONLY`
No es requisito. No sustituye ni sobrescribe V1, V2, Bridge, Resolution ni documento histórico.
`CODE_CHANGE_ALLOWED = NO` · `MODEL_DESIGN_ALLOWED = YES (P1–P4)` · `LIMITED (P5–P7)`
`COLLECTOR_CHANGED = NO` · `TESTS_CHANGED = NO` · `README = UNCHANGED` · `COMMIT = NO`
`AGENTS.md` = `a8b8ae64…` (modificado en la fase anterior de esta misma sesión, **no** en esta)

---

## 1 · CURRENT_ATTRIBUTION_MODEL

Verificado contra el código. **El nombre de una variable no se usa como prueba de lo que mide.**

| # | Actual | Propiedad que **realmente** mide | Unidad | Fuente de evidencia | Consumidor | Estado |
|---|---|---|---|---|---|---|
| 1 | `root_visibility_complete` (`:2585`) | Cobertura de lectura del barrido `/proc`: 0 fd denegados, 0 otros errores, 0 permisos en la corrida, 0 previos sin resolver | **proceso** (agregado) | `readlink` sin excepción; `unresolved_prior` del bundle padre | `card_complete`, `render_complete`, `g02` | PASS/FAIL |
| 2 | `card_target`/`render_target` (`:2772-2773`) | Identidad del nodo, derivada de sysfs | **nodo** | `GPU_PCI_TARGET` (vendor/device/BDF/class/**driver=amdgpu**) | `node_fd_count`, `node_attributable` | `gpu_proven` |
| 3 | `node_fd_count[target]` (`:2779`) | Nº de **descriptores** del proceso apuntando al nodo | **FD** | symlink `/proc/<pid>/fd/<n>` | la igualdad de `:2788-2789` | contador |
| 4 | `node_attributable[target]` (`:2783`) | Nº de FDs del nodo con **≥1** de los 3 campos | **FD** | texto de `/proc/<pid>/fdinfo/<n>` | igualdad + `card_clients` | contador |
| 5 | `card_attributable` (`:2788`) | `attributable == fd_count` **para card1** | **FD** | 3 y 4 | `card_complete` | booleano |
| 6 | `render_attributable` (`:2789`) | ídem **para renderD129** | **FD** | 3 y 4 | `render_complete` | booleano |
| 7 | `card_complete` (`:2839`) | `root_visibility_complete and card_attributable` | flag ∧ bool | 1 y 5 | `ownership_matrix:1702` | PASS/FAIL/NOT_EVALUATED |
| 8 | `render_complete` (`:2840`) | `root_visibility_complete and render_attributable` | flag ∧ bool | 1 y 6 | `ownership_matrix:1707` | PASS/FAIL/NOT_EVALUATED |
| 9 | `card_clients` (`:2869`) | = `node_attributable[card]` → nº de **FDs** que pasan el predicado | **FD** (¡no client!) | 4 | `ownership_matrix:1721` como **"N attributable client(s)"** | contador |
| 10 | `render_clients` (`:2870`) | ídem para render | **FD** | 4 | `:1722` | contador |
| 11 | `DRM_ATTRIBUTION_FIELDS` (`:1033`) | `("drm-client-id","drm-pdev","pasid")` — **tres campos de tres relaciones distintas** | — | — | `fdinfo_attribution:1052` | constante |
| 12 | `any(...)` (`:2783`) | `∃field ∈ 3` por FD | — | `fdinfo_attribution` | 4 | **único umbral de atribución** |
| 13 | `missing[]` (`:1659-1668`) | 4 comprobaciones **independientes** que acumulan razones | **pooled**, ambos nodos | contadores `coverage` | `drm_fds_enumerated` | reason-accumulator |
| 14 | `drm_fds_enumerated` (`:1576`) | Enumeración + atribución **pooled** | cliente/FD pooled | 13 | `ownership_matrix` | PASS/PARTIAL/UNKNOWN |
| 15 | `gpu_clients` (`:2455-2472`) | Lista de FDs DRM: `resource`=target del symlink, `fdinfo`=texto leído (**`""` si falló**) | **FD** | `scan_fds` | 3, 4 | lista |

### 1.1 Hallazgo del inventario

**La fila de nodo no es `any()` ni `all()`: es `∀fd∈nodo : ∃field∈3 : field ∈ fdinfo(fd)`.**

`:2788` compara `node_attributable[n] == node_fd_count[n]` → **universal sobre FDs**; `:2783` evalúa
`any(...)` → **existencial sobre campos**. Se combinaron un cuantificador universal con uno
existencial, y el existencial spans tres relaciones ajenas. Por eso ningún umbral era defendible, y
por eso el debate `any()`/`all()` estaba mal planteado desde el origen.

### 1.2 Mislabelling confirmado en el inventario

`card_clients` **cuenta FDs** y se consume como **"N attributable client(s)"** (`:1721`).
Con dos FDs del mismo `drm_file` (dup/fork), la fila diría **2 clients** donde hay **1**
`drm_file`/`drm-client-id`. `FD_COUNT ≠ CLIENT_COUNT`.

---

## 2 · DECOMPOSED_MODEL

### P1 · NODE_COMPLETENESS

| | |
|---|---|
| `DEFINITION` | La tabla de descriptores del proceso pudo enumerarse completa y ningún descriptor quedó sin resolver |
| `UNIT` | proceso (agregado) y descriptor (individual) |
| `SOURCE` | `SOURCES_OF_RECORD` (`proc_pid_fd(5)`: *"one entry for each file which the process has open"*; `PTRACE_MODE_READ_FSCREDS`) |
| `PRODUCER` | `root_fd_permission_denied`, `root_fd_other_errors`, `current_run_permission_denied`, `unresolved_prior` |
| `CONSUMER` | las dos filas de nodo; `g02` |
| `OBSERVABILITY` | `HIGH` — es la lectura que el collector ya hace |
| `PROVENANCE` | `HUMAN_REQUIREMENT` ("complete") + `EXTERNAL_DOCUMENTATION` |
| `STATUS` | `ESTABLISHED` |
| `PASS` | todos los FDs del proceso leídos y resueltos |
| `FAIL` | algún `readlink` o `listdir` falló, o una tabla entera quedó ilegible |
| `PARTIAL` | **no aplica**: hoy es booleano |
| `UNKNOWN` | el proceso no pudo observarse (fuera del universo observable) |
| `FALSIFIER` | que un FDs sin resolver no completara la tabla; o que `PTRACE_MODE_READ_FSCREDS` no gobernara esa lectura |

### P2 · NODE_PCI_IDENTITY

| | |
|---|---|
| `DEFINITION` | El nodo observado corresponde al dispositivo PCI de la RX550 |
| `UNIT` | nodo (`drm_minor`) |
| `SOURCE` | `AGENTS.md:32` + `drm-internals`: `drm_file.minor` → `drm_device` → `dev` (struct device) → BDF |
| `PRODUCER` | `GPU_PCI_TARGET` (vendor `0x1002`, device `0x699f`, BDF `0000:01:00.0`, class `0x030000`, driver `amdgpu`) + descubrimiento de nodos forward/reverse |
| `CONSUMER` | `gpu_proven` → gate de las dos filas |
| `OBSERVABILITY` | `HIGH` — **sin leer fdinfo** |
| `PROVENANCE` | `HUMAN_REQUIREMENT` (literal) + `EXTERNAL_SPEC` |
| `STATUS` | `ESTABLISHED` — **única propiedad con `HUMAN_REQUIREMENT` textual** |
| `PASS` | BDF+vendor+device+class+driver coinciden y el nodo se derivó de sysfs |
| `FAIL` | el nodo no se pudo probar para la RX550 |
| `PARTIAL` | no aplica |
| `UNKNOWN` | sysfs ilegible |
| `FALSIFIER` | que la identidad por BDF no determinara el dispositivo |

### P3 · DRM_CLIENT_IDENTITY

| | |
|---|---|
| `DEFINITION` | Existe al menos un `struct drm_file` identificable, y para cada FD del nodo puede afirmarse si pertenece a un cliente ya identificado |
| `UNIT` | **`struct drm_file`**, identificado por `drm-client-id` |
| `SOURCE` | `drm_file.c`: `client_id = atomic64_inc_return(&ident)`; `drm-usage-stats`: *"map 1:1 to … `struct drm_file`"*; `drm-internals`: `filelist` = *"List of userspace clients"* |
| `PRODUCER` | `fdinfo_attribution` **restringido a `drm-client-id`**, más deduplicación por `client-id` |
| `CONSUMER` | las dos filas de nodo |
| `OBSERVABILITY` | `MEDIUM` — observado 12/12, pero **sin texto crudo preservado** en ningún bundle |
| `PROVENANCE` | `EXTERNAL_SPEC` + `KERNEL_IMPLEMENTATION` |
| `STATUS` | `ESTABLISHED` la relación · **`REQUIREMENT_UNRESOLVED`** si debe exigirse (G-4: el campo es `optional`) |
| `PASS` | todo FD del nodo tiene `drm-client-id` presente, y el nº de client-ids distintos es coherente |
| `FAIL` | algún FD sin `drm-client-id` |
| `PARTIAL` | fdinfo ilegible en algún FD (ni presente ni ausente) |
| `UNKNOWN` | `gpu_proven` falso |
| `FALSIFIER` | que `drm-client-id` no fuera 1:1 con `drm_file`; o que su ausencia no debiera thwart la fila |

### P4 · PROCESS_ASSOCIATION

| | |
|---|---|
| `DEFINITION` | El proceso que **actualmente** usa cada `drm_file` observado es conocido |
| `UNIT` | descriptor ↔ proceso |
| `SOURCE` | `drm-internals`: `drm_file.pid` = *"Process that is using this file"*; `drm_file.c`: `pid = get_pid(task_tgid(current))` **y `drm_file_update_pid()` lo re-apunta** |
| `PRODUCER` | la ruta `/proc/<pid>/fd/<n>` (única superficie observable) |
| `CONSUMER` | las dos filas de nodo |
| `OBSERVABILITY` | `HIGH`, **con la salvedad de que `drm_file.pid` no es consultable y es mutable** |
| `PROVENANCE` | `EXTERNAL_SPEC` + `KERNEL_IMPLEMENTATION` |
| `STATUS` | `ESTABLISHED` la relación · **`REQUIREMENT_UNRESOLVED`** si la fila debe exigirla |
| `PASS` | cada FD observado tiene proceso propietario legible |
| `FAIL` | algún FD sin proceso |
| `PARTIAL` | el proceso desapareció entre la enumeración y la lectura |
| `UNKNOWN` | `gpu_proven` falso |
| `FALSIFIER` | que `/proc/<pid>/fd/<n>` no identificara el proceso; o que `drm_file.pid` fuera inmutable (es mutable) |

### P5 · VM_PASID_ASSOCIATION

`STATUS = SOURCE_INCOMPLETE`

| | |
|---|---|
| `DEFINITION` | Relación observable entre `amdgpu_vm`/`PASID` y un proceso |
| `UNIT` | vmid |
| `SOURCE` | **Documental únicamente**: *"The pasid is used to link a vmid to a system process id. If the process is active when the fault happens, the process information will be printed."* |
| `PRODUCER` / `CONSUMER` | **`NOT_ESTABLISHED`** |
| `OBSERVABILITY` | `LOW` —condicionada y episódica |
| `PROVENANCE` | `EXTERNAL_SPEC` (AMDGPU docs) |
| `ESTABLISHED` | `PASID` identifica un **vmid**; sirve para **enlazar vmid ↔ PID durante un page fault**; la impresión del proceso es **condicional**; `vmid 0` ⇒ driver/firmware |
| `FUENTE FALTANTE` | `amdgpu_drv.h` (struct `amdgpu_fpriv`, `amdgpu_vm`, `task_info`) y `amdgpu_vm.c` (`amdgpu_pasid_get_fpriv_locked`, `amdgpu_vm_get_task_info_pasid`, `amdgpu_vm_set_task_info`) — **404 en 4 hosts, bot-wall en 2** |
| `NO` | **no se convierte en propiedad de atribución de las filas de nodo** |

### P6 · MEMORY_CLIENT_STATS

`ESTABLISHED` a nivel de cliente. **La relación memoria → proceso NO está establecida.**

| | |
|---|---|
| `UNIT` | cliente (`drm_file`) |
| `SOURCE` | `drm-usage-stats`: `drm-total-<region>`, `drm-shared-<region>`, `drm-resident-<region>`, `drm-active-<region>`; `drm_file.c`: `drm_show_memory_stats` itera `file->object_idr` y separa `shared`/`private` |
| `ESTABLISHED` | las estadísticas son **por cliente**; `drm-active ⊆ drm-resident`; `drm-total` = buffers *solicitados*, no necesariamente materializados; shared/private es **derivado**, no propiedad del objeto |
| `NO ESTABLECIDO` | `memoria → proceso`; `memoria → drm_file` **exclusiva** (import dma-buf lo rompe) |
| `PROVENANCE` | `EXTERNAL_SPEC` + `KERNEL_IMPLEMENTATION` |
| `OBSERVABILITY` | `MEDIUM` (mismo límite de texto no preservado) |
| `FALSIFIER` | que la spec definiera alguna clave de memoria por proceso — no la define |

### P7 · ENGINE_CLIENT_STATS

`ESTABLISHED` a nivel de cliente y **como estadística acumulada**. **La relación engine → proceso NO está establecida.**

| | |
|---|---|
| `UNIT` | cliente (`drm_file`) |
| `SOURCE` | `drm-usage-stats`: `drm-engine-<key>` = *"time … the respective GPU engine spent busy executing workloads belonging to this client"*; *"Values are **not required to be constantly monotonic**"* |
| `ESTABLISHED` | la unidad es el **cliente**; es **tiempo acumulado**, no actividad actual |
| **`engine = 0` NO implica** | que el cliente no use la GPU. La no-monotonía obliga a retener el máximo anterior: un 0 tras un valor alto puede ser un retrocesoAllowed, no ausencia |
| **`engine > 0` SÍ implica** | trabajo ejecutado belonging a ese cliente |
| `NO ESTABLECIDO` | `engine → proceso`; `job → proceso`; `proceso → engine` |
| `OBSERVABILITY` | `LOW` — el collector **no recolecta** `drm-engine-*` |
| `FALSIFIER` | que `drm-engine-*` fuera por proceso; o que no fuera monotónico |

### P8 · CLIENT_PROCESS_RELATION

`STATUS = DERIVED` — **no es una tercera fuente de evidencia**.

| | |
|---|---|
| `DEFINITION` | Relación entre un cliente identificado y el proceso que lo usa |
| `SOURCE` | **compuesta**: P3 (el `drm_file` existe y tiene id) + P4 (el proceso es observable) |
| `PROVENANCE` | `INFERENCE` por composición de dos relaciones `ESTABLISHED` |
| `CONSECUENCIA` | se mantiene como **relación derivada documentada**; no habilita evidencia nueva ni un predicado nuevo |
| `FALSIFIER` | que P3 o P4 dejaran de estar establecidas |

---

## 3 · CARD vs RENDER — FASE 4

| | CARD (`card1`) | RENDER (`renderD129`) |
|---|---|---|
| `NODE_COMPLETENESS` | `root_visibility_complete` (**compartida, y legítimamente**) | idem |
| `NODE_PCI_IDENTITY` | mismo `drm_device`, mismo BDF | idem |
| `CLIENT_EVIDENCE` | `card_attributable` — **cálculo propio** | `render_attributable` — **cálculo propio** |
| `drm_master` | sí (`drm_is_primary_client`) | **no** — los render nodes no tienen master |

**¿Hay razón técnica para compartir?** Sí, y solo una: **P1 y P2 son propiedades del barrido y del
dispositivo, no del nodo**. La completitud de la lectura no depende de *qué* nodo se mira, y la
identidad PCI es del `drm_device`, que es el mismo para card y render. Eso es correcto y debe
conservarse.

**No hay razón para compartir `CLIENT_EVIDENCE`**, y ya **no** se comparte: `:2788` y `:2789` son
cálculos separados sobre `card_target` y `render_target`. Compartirlo fue el defecto corregido en la
corrección de Opción A; los tests `B`/`C` de esa corrección lo demuestran por ejecución.

**Relación estructural verificada**: un `drm_file` pertenece a **exactamente un** `minor`
(`drm_is_primary_client()`/`drm_is_render_client()` comparan `drm_file.minor`). Por tanto **un cliente
no puede pertenecer a ambos nodos**, y la evidencia de cliente de card y de render son **conjuntos
disjuntos**. Esto **refuta** el mundo sintético que construí en la primera ronda.

---

## 4 · TERMINOLOGÍA FIJADA — FASE 5

| Término | Significado exacto | Prohibido usarlo para |
|---|---|---|
| **`drm_file` / DRM client** | un `struct drm_file`; *"tracks DRM state per open file descriptor"* | el proceso, el FD, el `drm_master` |
| **`drm-client-id`** | `u64`, contador **global por boot**, 1:1 con `drm_file` | el proceso, el FD, el PASID |
| **`drm_master`** | proprietor de recursos de **display** por leasing; solo en primary node | atribución de workloads, identidad de cliente |
| **AMDGPU page-fault client ID** | el **GPU block** que causó el fault (`TCP`, `SDMA`, `VCN`…) | un cliente DRM |
| **`pasid`** | un **vmid**; enlaza vmid↔PID en un fault | identidad de cliente, identidad de proceso |
| **FD** | índice en una tabla de descriptores | un cliente, un `drm_file` |
| **proceso** | `task_tgid`, el *current holder* de un `drm_file` | identidad estable |

Donde "client" aparezca sin más en documentación nueva, debe llevar el calificador.

---

## 5 · PASID — FASE 7

`DRM_CLIENT_IDENTITY ≠ VM_PASID_ASSOCIATION`, y esa desigualdad está **establecida**:

| | |
|---|---|
| `PASID` identifica | un **vmid** (espacio de direcciones de GPU) |
| Su propósito documentado | *"link a vmid to a system process id"* |
| Cuándo existe la relación | **solo durante un page fault**, y **solo si el proceso está activo** en ese instante |
| Relación con `drm_file` | **`NOT_ESTABLISHED`** — ninguna fuente leída la enlaza |
| Relación con `drm-client-id` | **`REFUTADA`**: aquel es un contador global por boot, no un identificador de espacio de direcciones |
| Relación con `drm_file.pid` | **`REFUTADA`**: aquel es un `struct pid` reasignable, no un vmid |
| `SOURCE_INCOMPLETE` | falta el puente en `amdgpu_drv.h` / `amdgpu_vm.c` |

**No se intenta resolver P5 buscando más fuentes**: la evidencia ya permite clasificarla honestamente.

---

## 6 · RECOMMENDED_IMPLEMENTATION_MODEL

Sin supercategoría. Seis propiedades, sin `DRM_ATTRIBUTION_FIELDS` como umbrella.

```
NODE   : P1 NODE_COMPLETENESS   · P2 NODE_PCI_IDENTITY
CLIENT : P3 DRM_CLIENT_IDENTITY                      (unit = drm_file)
PROCESS: P4 PROCESS_ASSOCIATION                      (unit = fd-entry)
VM/PASID: P5  NO MODEL — SOURCE_INCOMPLETE
MEMORY : P6  per-client only; NO process attribution
ENGINE : P7  per-client, accumulated; NO process attribution
```

### CURRENT → PROBLEM → REPLACEMENT → MIGRATION IMPACT

| | |
|---|---|
| **HISTORICAL (INVALIDATED 2026-09-26)** | `DRM_ATTRIBUTION_FIELDS` (`:1033`) alimentaba `any()` (`:2783`), que alimentaba `node_attributable` y las dos filas. **RETIRADO**: el campo y el predicado compuesto fueron eliminados del collector; `card_clients`/`render_clients` dejaron de contar clients. No leer como estado actual |
| **PROBLEM** | La tupla mezcla **tres relaciones**: `client_id`↔`drm_file`; `pdev`→`drm_device`; `pasid`↔vmid-en-fault. `pdev` es **redundante** (P2 ya está por sysfs). `pasid` **no pertenece** a la relación del cliente. El predicado es `∀fd : ∃field`, un híbrido de cuantificadores |
| **REPLACEMENT** | P3 se computa **solo** con `drm-client-id`, deduplicado por `client-id` para el recuento. P2 sigue siendo el gate, leído de sysfs, **no** de fdinfo. `pasid` se **retira** de la semántica de las filas de nodo y queda como dato de otra relación |
| **MIGRATION IMPACT** | El campo `card_clients` pasa a **contar client-ids distintos** en lugar de FDs: la deduplicación es posible con la evidencia ya recolectada (cada entrada tiene su `fdinfo`), **sin campo nuevo**. `DRM_ATTRIBUTION_FIELDS` puede conservarse como lista de campos *reportados*, nunca como criterio de fila |

### Semántica por propiedad

| | PASS | FAIL | PARTIAL | UNKNOWN |
|---|---|---|---|---|
| **P1** | 0 lecturas fallidas | ≥1 fallida | n/a | proceso no observado |
| **P2** | BDF+vendor+device+class+driver coinciden | no | n/a | sysfs ilegible |
| **P3** | todo FD del nodo tiene `drm-client-id` | alguno no lo tiene | fdinfo ilegible en algún FD | `gpu_proven` falso |
| **P4** | todo FD tiene proceso legible | alguno no | proceso desapareció a mitad | `gpu_proven` falso |

**Dependencias**: P3 y P4 **requieren P1** para ser observables — no son independientes en el sentido
de "pueden fallar por separado". `FALSIFIER` de la independencia: P3 no puede evaluarse sin haber
leído la tabla.

---

## 7 · RECOMMENDED_TEST_MODEL

Cada test prueba **una** propiedad y ninguno se limita a comprobar que una clave existe.

| # | Mundo | Prueba | No debe cambiar |
|---|---|---|---|
| 1 | nodo completo + PCI | P1 ∧ P2 PASS | P3, P4 |
| 2 | nodo incompleto + PCI | P1 FAIL ⇒ filas FAIL aunque P3 PASS | — |
| 3 | `client-id` presente | P3 PASS | P1, P2, P4 |
| 4 | `client-id` ausente, resto presente | P3 **FAIL** — y `pdev`/`pasid` presentes **no** lo salvan | P1, P2 |
| 5 | asociación de proceso presente | P4 PASS | P3 |
| 6 | asociación de proceso ausente | P4 FAIL, P3 PASS | — |
| 7 | 2 FDs → 1 `client-id` | `card_clients == 1`, y la fila no cuenta 2 | — |
| 8 | 2 `drm_file` → mismo PID | `client-id` distintos ⇒ 2 clientes | — |
| 9 | `pasid` ausente + `client-id` presente | **P3 PASS** — `pasid` no participa | — |
| 10 | `pasid` presente sin `client-id` | **P3 FAIL** | — |
| 11 | card PASS / render FAIL | independencia de P3 por nodo | P1, P2 |
| 12 | card FAIL / render PASS | ídem | — |
| 13 | stats de memoria de cliente | P6 por cliente; **no** attributable a proceso | filas de nodo |
| 14 | stats de engine de cliente | P7 por cliente | filas de nodo |
| 15 | `engine = 0` | P7 **no** implica ausencia de uso; filas de nodo **no** cambian | P1–P4 |
| 16 | `engine > 0` | P7 sí implica trabajo del cliente | P1–P4 |

Tests 7 y 8 son los que **hoy no existen** y son los que fijan F-02.

---

## 8 · SELF_CRITIQUE — FASE 11

Defectos encontrados **en mi propio modelo**, corregidos antes de entregarlo:

**S-1 · Un PASS derivado de ausencia de evidencia.** El modelo vigente tiene
`card_attributable = (0 == 0) = True` para un nodo **sin FDs**. Eso hace que P3 lea **PASS** cuando
**no se observó ningún cliente** — confunde *"no hay clientes"* con *"los clientes están
identificados"*. Es exactamente el error que `AGENTS.md` prohíbe. **Corrección**: P3 con 0 FDs debe
emitir un estado distinto de PASS (o la fila debe reportar aparte "0 clientes observados"), y ese caso
no puede compartir veredicto con "todos atribuidos".

**S-2 · P3 `FAIL` por un campo `optional`.** Exigir `drm-client-id` hace que un driver conforme a la
spec que lo omita produzca `FAIL` permanente. Es un **riesgo de falso negativo** real y es el hueco
G-4 ya registrado. **Corrección**: el modelo declara `PASS_SEMANTICS` como *derivada* de una decisión
humana pendiente, no como encontrada. No se propone PASS/FAIL definitivo para P3.

**S-3 · Presenté P1–P4 como "separadas" cuando P3/P4 dependen de P1.** La palabra "independientes"
es engañosa: sin lectura completa no hay nada que atribuir. **Corrección**: la dependencia está
declarada explícitamente en §6 y el test model no promete independencia, promete **atribución de la
causa del cambio a una sola propiedad**.

**S-4 · Usé el nombre `card_clients` como si su unidad fuera clientes.** Es el mismo error que critico
en el código. **Corrección**: en §1 lo marqué explícitamente como contador de **FDs** con etiqueta
engañosa, y F-02 queda como finding abierto, no como nombre a cambiar.

**S-5 · `P8` podía leerse como evidencia nueva.** Lo degradé a `DERIVED`, con la advertencia de que
no habilita predicado propio.

**No encontré** otra mezcla de propiedades, ni `pasid`/proceso/memoria/engine cruzados con la
identidad, ni dependencia accidental entre card y render más allá de la **justificada** (P1/P2 son
del barrido y del dispositivo).

---

## 9 · REFUTED_CLAIMS

| Claim | Evidencia que lo refuta | Estado |
|---|---|---|
| "Un mismo cliente puede estar en `card1` y `renderD129`" | un `drm_file` tiene **un** `minor` | **REFUTADO** |
| "La fila es `any()` o `all()`" | es `∀fd : ∃field` | **REFUTADO** |
| "Existe un `all()` de atribución" | no existe; hay 4 `if` independientes | **REFUTADO** |
| "`pasid` es identidad de cliente" | pertenece a `vmid↔PID` en un fault | **REFUTADO** |
| "`card_clients` cuenta clientes" | cuenta FDs | **REFUTADO** |
| "La unidad de atribución es el FD" | la unidad del `client-id` es `drm_file` | **REFUTADO** |
| "El agente no criticaba prompts" | sí lo hacía, sin regla que lo obligara | **REFUTADO** |

## 10 · CONFLICTS

`C-1` `drm-client-id` vs *client ID* de page fault (GPU block) — **`CONFLICT_UNRESOLVED`**.
`C-2` tres sentidos de "client" — **`CONFLICT_UNRESOLVED`**. Ambos son colisiones de término; la
terminología fijada en §4 los mitiga **documentalmente**, no los resuelve en el kernel.

## 11 · OPEN

1. **G-4** — ¿debe P3 exigir `drm-client-id`, siendo `optional` en la spec? **`REQUIREMENT_UNRESOLVED`**.
2. **S-1** — estado de P3 cuando el nodo tiene 0 FDs. **Decisión de diseño**, no cerrada aquí.
3. **G-1/G-2** — si la fila de nodo debe exigir **cliente**, **proceso**, o ambos. **`REQUIREMENT_UNRESOLVED`**.
4. **C-1/C-2** — sin resolver en upstream.

## 12 · BLOCK

- **P5** `SOURCE_INCOMPLETE`. Input: `linux-source` de Debian/Ubuntu, o `.tar.xz` de `archive.ubuntu.com`.
- **P6/P7 → proceso** `NOT_ESTABLISHED` sin fuente nueva posible: **no es un bloqueo, es un límite de la spec** (ella define la unidad como cliente).
- **P3 PASS/FAIL** bloqueado por G-4.
- **F-02** (nombre y conteo) bloqueado por `CODE_CHANGE_ALLOWED = NO`.

## 13 · NEXT

**Una sola acción**: responder **G-4** — *¿una fila de nodo debe exigir `drm-client-id` por descriptor,
siendo un campo `optional` de la spec?* Es la entrada que desbloquea `PASS_SEMANTICS` de P3, y con ella
el modelo, el test model y F-02. G-1/G-2 pueden resolverse después sin bloquear este paso.
