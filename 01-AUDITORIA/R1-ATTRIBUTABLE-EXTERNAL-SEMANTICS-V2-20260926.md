# R1-ATTRIBUTABLE-EXTERNAL-SEMANTICS-V2-20260926

`DOCUMENT_KIND = RESEARCH` · `NORMATIVE_STATUS = RESEARCH_ONLY`
No es requisito ni propuesta de requisito. No sustituye `AGENTS.md`,
`R1-ATTRIBUTABLE-NODE-ROWS-REQUIREMENT-20260926.md`,
`R1-ATTRIBUTABLE-DEFINITION-RESEARCH-20260926.md` ni
`R1-ATTRIBUTABLE-EXTERNAL-SEMANTICS-20260926.md`. No sobrescribe ninguno.
`CODE_CHANGED = NO` · `COLLECTOR_CHANGED = NO` · `TESTS_CHANGED = NO` · `AGENTS.md = UNCHANGED`
`HOST_MEASUREMENT = NONE` · `COMMIT = NO`

> No se declara `PASS`/`FAIL` de ninguna implementación. No se propone solución.

---

## 1 · EXECUTIVE_FINDING

Tres resultados, en orden de peso:

**(a) `PASID` tiene un propósito documentado, y no es el que el proyecto le atribuyó.**
Documentación oficial de amdgpu: *"The **pasid is used to link a vmid to a system process id**. If
the process **is active when the fault happens**, the process information will be printed."*
Es decir: la relación `PASID → process` está documentada **en el contexto de un page fault**, y es
**condicional** a que el proceso esté activo en ese instante. No es un mecanismo de atribución
permanente ni consultable fuera de un fault.

**(b) "client ID" significa dos cosas incompatibles, en la misma pila de software.**
- `drm-client-id` (`drm-usage-stats`): *"map 1:1 to the in kernel representation of `struct
  drm_file`"* — identifica un **cliente DRM**.
- `client ID` en un page fault de amdgpu (`amdgpu/debugging`): *"The client ID indicates the **GPU
  block** that caused the fault"* — lista `CB/DB, CPF, CPC, CPG, TCP/SQC/SQG, SDMA, VCN, JPEG`.
  Es un **cliente de memoria de hardware**, no un cliente DRM.

Cualquier definición de "atribuible" que use la palabra "client" sin desambiguar queda **ambigua por
construcción**.

**(c) `amdgpu_gem_info` y `amdgpu_vm_info` listan "PIDs using the GPU", pero la documentación no
define "using the GPU".** No hay puente documentado entre el PID de esas tablas y `drm_file` /
`drm-client-id`. Su semántica exacta es `NOT_ESTABLISHED`.

---

## 2 · RESEARCH_SCOPE

Búsqueda de semántica de "atribución" en documentación oficial de Linux DRM y AMDGPU, con el
objetivo de responder las 8 preguntas del criterio de calidad (§29 del encargo). Read-only.

## 3 · SOURCES_SEARCHED

| ID | Fuente | URL | Fecha acceso | Versión | Autoridad |
|---|---|---|---|---|---|
| S1 | `drm-usage-stats` | `docs.kernel.org/gpu/drm-usage-stats.html` | 2026-09-26 | 7.3.0-rc4 | `EXTERNAL_SPEC` |
| S2 | `drm-uapi` | `docs.kernel.org/gpu/drm-uapi.html` | 2026-09-26 | 7.3.0-rc4 | `EXTERNAL_SPEC` |
| S3 | `drm-internals` | `docs.kernel.org/gpu/drm-internals.html` | 2026-09-26 | 7.3.0-rc4 | `EXTERNAL_SPEC` |
| S4 | `amdgpu/debugging` | `docs.kernel.org/gpu/amdgpu/debugging.html` | 2026-09-26 | 7.3.0-rc4 | `EXTERNAL_SPEC` (AMDGPU) |
| S5 | `amdgpu/debugfs` | `docs.kernel.org/gpu/amdgpu/debugfs.html` | 2026-09-26 | 7.3.0-rc4 | `EXTERNAL_SPEC` (AMDGPU) |
| S6 | `amdgpu/index` | `docs.kernel.org/gpu/amdgpu/index.html` | 2026-09-26 | 7.3.0-rc4 | `EXTERNAL_SPEC` (AMDGPU) |
| S7 | `man5 proc_pid_fd` / `proc_pid_fdinfo` | `man7.org/linux/man-pages/man5/` | 2026-09-26 | man-pages 6.19 | `EXTERNAL_DOCUMENTATION` |
| S8 | `amdgpu/thermal` | `docs.kernel.org/gpu/amdgpu/thermal.html` | 2026-09-26 | 7.3.0-rc4 | `EXTERNAL_SPEC` — **irrelevante** (PM/thermal) |
| S9 | `AGENTS.md` | local | — | — | `HUMAN_REQUIREMENT` |
| S10 | evidencia de host preservada | `OWNERSHIP-AUDIT-HOST-C-20250925T231635Z.md:55-70`, `R1-C1-CORRECTION-CLOSURE-20260926.md:321-384` | 2025-09-25 / 2026-09-26 | — | `PROJECT_EVIDENCE` |

## 4 · SOURCES_UNAVAILABLE

| Fuente | Motivo | Consecuencia |
|---|---|---|
| `git.kernel.org` cgit | Anubis bot-wall | **Código fuente no consultado**: `drm_file`, `drm_show_fdinfo()`, `amdgpu_gem_info.c`, `amdgpu_vm_info.c` → `NOT_AVAILABLE` |
| `elixir.bootlin.com` | Anubis bot-wall | Ídem |
| `docs.kernel.org/admin-guide/dmem.html` | 404 | **`dmem` cgroup sin documentar** → `NOT_ESTABLISHED` |
| `amdgpu_top`, `nvtop`, `radeontop`, `umr`, `drm_info` | **4 búsquedas web → 0 resultados**; URLs adivinadas → 404 | **Herramientas no inspeccionadas** → cobertura nula |
| `Documentation/ABI/…debugfs-driver-amdgpu` | no alcanzado | Formato de salida de `gem_info`/`vm_info` no obtenido |

**Declaración de cobertura**: las secciones de herramientas (§15 del encargo) y de cgroup **no
investigadas**. Se reportan como hueco, no como ausencia.

---

## 5 · HUMAN_REQUIREMENT

| ID | Fuente | Texto |
|---|---|---|
| H-1 | `AGENTS.md:176` | *"complete attributable evidence for the RX550's card and render nodes, identified by PCI identity rather than by node name, plus user/root namespaces, **DRM FDs**, writers…"* |
| H-2 | `AGENTS.md:32` | *"Identify a device by PCI identity, never by its `cardN` name"* |
| H-3 | `AGENTS.md:103-104` | *"**Requirement: attribute DRM clients per process.** Formalisation: the row `clients_pasid_attributable`."* — **ejemplo** de disciplina de procedencia |
| H-4 | `AGENTS.md:176-178` | "DRM FDs" es un ítem **distinto** de "card and render nodes" |

**El requisito humano no enumera campos, ni unidades, ni umbrales.** H-3 es un ejemplo y su fuerza
normativa es `UNKNOWN`.

## 6 · AGENT_FORMALIZATION

| ID | Ubicación | Qué introduce |
|---|---|---|
| A-1 | `OWNERSHIP_CRITERION_ROWS` | "DRM card node FD table **complete and attributable**" |
| A-2 | `DRM_ATTRIBUTION_FIELDS` | `("drm-client-id","drm-pdev","pasid")` |
| A-3 | `drm_fd_enumeration_state` | umbral `all()` |
| A-4 | productor de nodo | umbral `any()` |
| A-5 | `card_clients` | nombre de campo que cuenta FDs |
| A-6 | `R1-PREFLIGHT:224`, `R1-PLAN:144` | "clients/PASID atribuibles \| **UNKNOWN** \| *a decidir*" — el proyecto ya lo marcó `UNKNOWN` en planificación |

**A-6 es precedente importante**: la decisión se aplazó explícitamente y nunca se tomó.

---

## 7 · EXTERNAL_SPEC

### 7.1 Cadena formal (`drm-internals`, S3) — `DIRECT_DEFINITION`

| Campo | Descripción literal |
|---|---|
| `drm_file` | *"This structure tracks DRM state **per open file descriptor**."* |
| `drm_file.pid` | *"**Process that is using this file.**"* |
| `drm_file.client_id` | *"**A unique id for fdinfo**"* |
| `drm_file.minor` | *"struct drm_minor for this file."* |
| `drm_file.filp` | *"Pointer to the core file structure."* |
| `drm_file.master` | *"Master this node is currently associated with… Only relevant if `drm_is_primary_client()` returns true."* |
| `drm_file.debugfs_client` | *"debugfs directory for **each client** under a drm node."* |
| `drm_device.filelist` | *"**List of userspace clients**, linked through `drm_file.lhead`."* |
| `drm_device.primary/.render/.accel` | los tres minors |
| `drm_device.dev` | *"Device structure of bus-device"* |
| `drm_is_primary_client()` | *"…i.e. **`drm_file.minor` of `file_priv` is a primary minor**."* |

### 7.2 `drm-client-id` (S1) — `DIRECT_DEFINITION`

*"Unique value relating to the open DRM file descriptor used to **distinguish duplicated and shared
file descriptors**. Conceptually the value **should map 1:1 to the in kernel representation of
`struct drm_file`**. Uniqueness shall be either globally unique, or **unique within the scope of
each device, in which case `drm-pdev` shall be present as well**."*

`drm-client-id` es **`OPTIONAL`**. `drm-pdev` es **`OPTIONAL`**. `drm-driver` es el **único
`MANDATORY`**.

### 7.3 `drm-engine-*` (S1) — `DIRECT_DEFINITION`

*"GPUs usually contain multiple execution engines. Each shall be given a stable and unique name…
Value shall be in specified time units that the respective GPU engine **spent busy executing
workloads belonging to this client**."* — y: *"Values are **not required to be constantly
monotonic**… userspace is expected to **stay with that larger previous value until a monotonic
update is seen**."*

**Consecuencias strictas**:
- La unidad es **el cliente**, no el proceso, no el FD.
- Es **tiempo acumulado**, no actividad actual.
- El valor **0** significa "0 ns acumulados en la ventana observada"; por la regla de no-monotonía,
  un 0 **no puede leerse** como "el proceso no está usando la GPU ahora".
- El propio documento de S1 dice que `drm-engine` no debe usarse para correlación de uso sin más.

### 7.4 Memoria (S1) — `DIRECT_DEFINITION`

| Clave | Define | No define |
|---|---|---|
| `drm-total-<region>` | total de buffers **solicitados** por el cliente; *"backing store does not need to be currently instantiated"* | **no** demuestra uso actual |
| `drm-shared-<region>` | memoria de un buffer *"shared with another file (i.e., have more than one handle)"* | **no** es propiedad exclusiva |
| `drm-resident-<region>` | backing store **materializado** | no demuestra actividad |
| `drm-active-<region>` | *"practical example of this could be the presence of unsignaled fences in a GEM buffer reservation object… the active category is a **subset** of the resident category"* | no implica proceso ejecutándose |

Las cuatro son **por cliente**, y el texto advierte explícitamente de **doble contabilización**:
*"To avoid double-counting, if a buffer has multiple regions… the implementation should
consistently select a single region"*.

### 7.5 AMDGPU: `pasid`, `vmid`, page fault (S4) — `DIRECT_DEFINITION`

*"Next you have the **vmid and pasid**. If the **vmid is 0**, this fault was likely caused by the
**kernel driver or firmware**. If the vmid is non-0, it is generally a fault in a **user
application**. **The pasid is used to link a vmid to a system process id. If the process is active
when the fault happens, the process information will be printed.**"*

Ejemplo literal del log:
`[gfxhub0] no-retry page fault (src_id:0 ring:24 vmid:3 pasid:32777, for process glxinfo pid 2424 thread glxinfo:cs0 pid 2425)`

| Consecuencia | Estado |
|---|---|
| `PASID` identifica un **vmid** (espacio de direcciones) | `ESTABLISHED` |
| `PASID` **enlaza vmid ↔ system process id** | `ESTABLISHED` |
| La impresión del proceso es **condicional** a que esté activo en el momento del fault | `ESTABLISHED` |
| La relación es **episódica** (solo durante un fault), no un registro consultable | `ESTABLISHED` |
| `vmid 0` ⇒ driver/firmware, **no** proceso de usuario | `ESTABLISHED` |
| Proceso ≠ thread: el ejemplo distingue `pid 2424` de `thread … pid 2425` | `ESTABLISHED` |
| `PASID` obtainable por `fdinfo` en condiciones normales | **`NOT_ESTABLISHED`** |
| `PASID` obligatorio para atribuir un FD | **`NOT_ESTABLISHED`** — y el texto sugiere lo contrario |

### 7.6 AMDGPU: "client ID" (S4) — `DIRECT_DEFINITION`, y colisión de término

*"The **client ID** indicates the **GPU block** that caused the fault."* Lista: `CB/DB, CPF, CPC,
CPG, TCP/SQC/SQG (Shaders), SDMA, VCN, JPEG`.

Es un **cliente de memoria de hardware**. No tiene relación con `drm-client-id`. La palabra
"client" designa aquí un **IP block del GPU**.

### 7.7 AMDGPU: `amdgpu_gem_info` / `amdgpu_vm_info` (S5) — `DIRECT_DEFINITION` parcial

| Archivo | Texto literal |
|---|---|
| `amdgpu_gem_info` | *"**Lists all of the PIDs using the GPU** and the GPU buffers that they have allocated. This lists the buffer size, pool (VRAM, GTT, etc.), and buffer attributes…"* |
| `amdgpu_vm_info` | *"Lists all of the PIDs using the GPU and the GPU buffers that they have allocated **as well as the status of those buffers relative to that process' GPU virtual address space** (e.g., evicted, idle, invalidated, etc.)."* |

**Lo que NO dice la documentación**:
- No define **"using the GPU"**.
- No menciona `drm_file`, `drm-client-id`, `drm-pdev` ni `pasid`.
- No documenta el formato de salida (columnas, campos).
- No establece puente con `/proc/<pid>/fdinfo`.

### 7.8 Actividad por engine: la noción mejor fundamentada (S5) — `DIRECT_DEFINITION`

`amdgpu_fence_info`: *"Rings with a larger **emitted** fence value have **outstanding work that is
still being processed** by the engine that owns that ring. When the **emitted and signalled** fence
values are equal, **the ring is idle**."*

Es una noción de **actividad por ring/engine**, formal y con condición de inactividad explícita.
**No** es por proceso: un ring pertenece a un `drm_file`/scheduler entity, no a un PID.

### 7.9 Nivel de dispositivo (S5, S6) — `DIRECT_DEFINITION`

- `amdgpu_pm_info`: "current GFX clock, Memory clock, voltages, average SoU power, temperature,
  **GFX load, Memory load**" → **nivel de dispositivo**, no por cliente.
- `mem_info_vram_used`, `mem_info_gtt_used` (S6) → **nivel de dispositivo**.
- `amdgpu_wave` → "GFX/compute wave information **from the hardware**" → nivel hardware.
- `amdgpu_gca_config` → "GPU details (Graphics/Compute Array config, **PCI config**, GPU family)".

**Conclusión**: AMDGPU documenta la atribución **por cliente** (fdinfo) y la **actividad por
engine/ring** (fences), pero **no** una atribución de engine a proceso.

---

## 8 · EXTERNAL_IMPLEMENTATIONS

| Proyecto | Estado | Autoridad |
|---|---|---|
| `umr` | **Mencionado** en S4/S5 como *"general purpose GPU debugging and diagnostics tool"* y *"Used by tools like UMR to decode the rings"*, *"to inspect objects in VRAM"*, *"to query GFX details"*. **No inspeccionado**: su documentación está fuera de docs.kernel.org y las búsquedas fallaron | `EXTERNAL_IMPLEMENTATION` (solo por mención documental) |
| `amdgpu_top`, `nvtop`, `radeontop`, `drm_info` | **NO CONSULTADOS** | `NOT_AVAILABLE` |

**Regla aplicada**: una implementación no es especificación. Como no se pudo inspeccionar ninguna,
esta sección **no aporta evidencia semántica**.

---

## 9 · RELATIONSHIP_MATRIX

| RELACIÓN | OBJETO A | OBJETO B | FUENTE | UNIDAD | OBSERVABLE | NECESARIA PARA | LIMITACIÓN | FALSIFICADOR |
|---|---|---|---|---|---|---|---|---|
| process → `drm_file` | proceso | `drm_file` | S3 `pid` | `drm_file` | sí (`/proc/<pid>/fd`, fdinfo) | **node-process** | `pid` es del proceso, no del thread | S3 dijera otra cosa |
| `drm_file` → FD | `drm_file` | descriptor | S3 `filp` | descriptor | sí | node-process | 1 `drm_file` por FD abierto | S3 no lo dijera |
| `drm_file` → `client_id` | `drm_file` | id | S1 | `drm_file` | sí (fdinfo) | client-attribution | `optional`; unicidad por dispositivo | S1 no lo asociara 1:1 |
| `drm_file` → nodo | `drm_file` | `drm_minor` | S3 `minor` | `drm_file` | sí (`/dev/dri/*`) | node | por **nombre**, no por PCI | S3 no lo dijera |
| nodo → BDF | `drm_minor` | PCI | S3 `dev` | `drm_device` | sí (sysfs) | **PCI** | requiere sysfs, no fdinfo | S3 no lo dijera |
| client → memoria | cliente | bytes | S1 `drm-total/-shared/-resident/-active` | cliente | sí (fdinfo) | memory | por cliente, no por proceso; doble contabilizaciónClient | S1 lo atribuera a proceso |
| client → engine | cliente | ns | S1 `drm-engine-*` | cliente | sí (fdinfo) | engine | **acumulado, no actual**; no monotónico | S1 lo definiera como actual |
| engine → proceso | — | — | — | — | **no** | — | **no existe relación formal documentada** | fuente que la>definiera |
| ring → actividad | ring | fences | S5 `amdgpu_fence_info` | ring | sí (debugfs) | engine | por **ring**, no por PID | S5 lo atribuyera a PID |
| PID → `gem_info` | PID | buffers | S5 | PID | sí (debugfs) | memory | "using the GPU" **no definido** | S5 lo definiera |
| PID → `vm_info` | PID | VA space | S5 | PID | sí (debugfs) | VM | estado relativo, **no** actividad | S5 lo definiera |
| `vmid` ↔ `PASID` | vmid | pasid | S4 | vmid | **solo en log de fault** | — | **episódico** | S4 no lo dijera |
| `PASID` → process | pasid | PID | S4 | PID | **condicional** | — | *"if the process is active when the fault happens"* | S4 no lo condicionara |
| `PASID` → `drm_file` | — | — | — | — | **no documentada** | — | `NOT_ESTABLISHED` | fuente que laestableciera |
| resource → cgroup | recurso | cgroup | S3 (`drmm_cgroup_register_region`) | cgroup | **no** (doc no obtenida) | — | `NOT_ESTABLISHED` | doc del controlador dmem |
| `drm_file` → `drm_master` | `drm_file` | master | S3 `master` | `drm_file` | **condicional** | — | *"Only relevant if `drm_is_primary_client()`"* | S3 no lo condicionara |

---

## 10 · CRITERIA_MATRIX

| Criterio | Def. externa | Def. humana | Def. implementada | Evidencia disp. | Discrepancia | Estado |
|---|---|---|---|---|---|---|
| **A. NODE_COMPLETENESS** | `listdir`+`readlink` sin fallos (S7) | H-1 "complete" | `root_visibility_complete` | alta | ninguna | `ESTABLISHED` |
| **B. NODE_PROCESS_ATTRIBUTION** | `drm_file.pid` (S3) + `/proc` (S7) | H-3 "per process" (ejemplo) | `any(...)` de 3 campos | alta | **la unidad**: implementada por FD, ejemplo dice por cliente | `PARTIALLY_DEFINED` |
| **C. DRM_CLIENT_ATTRIBUTION** | `drm-client-id` ↔ `drm_file` 1:1 (S1+S3) | H-3 | `any()` acepta `pasid` | media | **`pasid` no pertenece a esta relación** | `AMBIGUOUS` |
| **D. PCI_DEVICE_ATTRIBUTION** | `drm_device.dev` (S3) | **H-2 literal** | `gpu_proven` (sysfs) | **alta** | ninguna | `ESTABLISHED` |
| **E. MEMORY_ATTRIBUTION** | `drm-total/-shared/-resident/-active` **por cliente** (S1) | H-4 ("DRM FDs" aparte) | `clients_pasid_attributable` (debugfs) | media | **unidad**: memoria es por cliente, la fila dice per-process | `PARTIALLY_DEFINED` |
| **F. ENGINE_ACTIVITY_ATTRIBUTION** | `drm-engine-*` **por cliente, acumulado** (S1); `amdgpu_fence_info` **por ring** (S5) | ninguna | `NOT_EVALUATED` / `UNKNOWN` | **nula en el collector** | **no existe relación proceso→engine** | `NOT_ESTABLISHED` |
| **G. VM/CONTEXT_ATTRIBUTION** | `amdgpu_vm_info`: PID ↔ VA space (S5) | ninguna | `NOT_EVALUATED` | baja | "using the GPU" no definido | `NOT_ESTABLISHED` |
| **H. PASID_ATTRIBUTION** | vmid↔PASID↔PID, **episódico y condicional** (S4) | ninguna | `any()` lo acepta | **no reproducible** | el uso como predicado de fila no tiene base | `NOT_ESTABLISHED` |

---

## 11 · EDGE_CASE_MATRIX

| # | Caso | Qué puede afirmarse | Qué **NO** |
|---|---|---|---|
| 1 | 1 proc / 1 FD / 1 cid / pdev / PASID / engines | La cadena completa por `drm_file` | que PASID sea persistente |
| 2 | 1 proc / 2 FD / **1** cid | 2 FDs, **1** cliente (dup/shared) | 2 clientes |
| 3 | 1 proc / 2 FD / **2** cid | 2 `drm_file` distintos, mismo proceso | 1 cliente |
| 4 | 2 proc / mismo disp / cid distintos | 2 clientes | que uno "use" más que otro |
| 5 | fdinfo **sin** `drm-client-id` | el FD es de un nodo | que el campo sea obligatorio: es `optional` (S1) |
| 6 | cid **sin** `drm-pdev` | el id puede ser globalmente único (S1) | que falte identidad de dispositivo por eso: ya está por sysfs |
| 7 | pdev **sin** cid | el FD apunta a un PCI | que sea atribuible a cliente |
| 8 | **PASID sin cid** | un vmid existe | **nada** sobre cliente |
| 9 | cid presente, **engines = 0** | 0 ns acumulados | **que el proceso no use la GPU**: no-monotonía (S1) |
| 10 | memoria > 0, engine = 0 | tiene buffers solicitados | actividad |
| 11 | engine > 0, memoria = 0 | submits ejecutados | que deba tener VRAM |
| 12 | PID en `gem_info`, sin FD visible | el kernel lo lista usando GPU | que tenga `drm_file` (no documentado) |
| 13 | PID en `vm_info`, sin FD visible | tiene VA space y buffers | que tenga `drm_file` (no documentado) |
| 14 | proceso desaparece | — | nada: la disappeared no es prueba (§V3) |
| 15 | fdinfo ilegible | cobertura perdida | ausencia de cliente |
| 16 | **varios FD → mismo cliente** | 1 cliente | N clientes |

---

## 12 · F01_ANALYSIS

F-01asked: `any(drm-client-id, drm-pdev, pasid)` en filas de nodo vs
`all(drm-client-id, drm-pdev, pasid)` en `drm_fds_enumerated`.

**¿Existe una definición externa que lo resuelva? → NO.**

Evidencia:
1. `pasid` pertenece, por S4, a la relación **`vmid ↔ process durante un page fault**. No pertenece
   a `drm_file`, ni a `client_id`, ni a la cadena de nodo.
2. `drm-pdev` pertenece a la relación **`drm_file.minor → drm_device`**, que el collector ya
   establece por sysfs sin leer fdinfo.
3. `drm-client-id` pertenece a la relación **`drm_file ↔ client_id`**, y es `optional`.
4. Los tres campos **no son una familia**: pertenecen a tres relaciones distintas.

**`F-01 = REQUIREMENT_UNRESOLVED`.** Y esta ronda añade un agravante: el uso de `pasid` en un
predicado de fila de nodo no solo es `NOT_ESTABLISHED`, sino que **pertenece a otra relación**.

## 13 · F02_ANALYSIS

`card_clients` cuenta FDs. Unidad correcta por contexto:

| Contexto | Unidad correcta | Fuente |
|---|---|---|
| "clients DRM de la RX550" | `drm_file` distintos = `drm-client-id` distintos | S1 + S3 |
| "descriptors sobre la RX550" | FDs | S7 |
| "recursos de memoria" | **cliente** | S1 |

Evidencia de host (S10): kwin_wayland = **1 proceso, 9 FDs, 3 ids**. Los tres conteos difieren.

**F-02 confirmado**; la corrección de nombre sigue siendo una decisión de implementación, no de esta
investigación.

## 14 · PASID_ANALYSIS

`PASID_SEMANTICS = PARTIALLY_DEFINED` (mejora respecto de `NOT_ESTABLISHED` de la ronda anterior).

| | |
|---|---|
| **Qué identifica** | Un **vmid**, es decir un espacio de direcciones virtual de GPU |
| **Relación con PID** | *"used to link a vmid to a system process id"* |
| **Condición** | *"If the process **is active when the fault happens**"* |
| **Persistencia** | **Episódica**: solo durante un page fault. No hay registro consultable |
| **Por proceso** | Sí, a **proceso**; el thread es separado en el ejemplo (`pid 2424` vs `pid 2425`) |
| **Varios PASID por proceso** | **`NOT_ESTABLISHED`** |
| **PASID compartido** | **`NOT_ESTABLISHED`** |
| **Atribuir un FD con PASID** | **`NOT_ESTABLISHED`** — no hay relación documentada `PASID ↔ drm_file` |
| **Obligatorio para atribución** | **NO, y la fuente sugiere lo contrario**: su función es *enlazar* vmid con PID en un fault |

**Corrijo un premise del encargo**: el triple `VMID / PASID / system PID` documentado por AMD
**no está en la documentación de `amdgpu_gem_info`/`amdgpu_vm_info`**, sino en la de **decodificación
de page faults**. Son contextos distintos.

## 15 · ENGINE_ANALYSIS

| Afirmación | ¿Se puede? | Evidencia |
|---|---|---|
| "PID X usa GFX" | **NO** | no hay relación proceso→engine documentada |
| "PID X tiene un contexto GFX" | parcial, vía `vm_info` | S5, pero "using the GPU" no definido |
| "PID X tiene un cliente DRM con actividad GFX" | **SÍ**, con reserva | S1: `drm-engine-*` es por cliente y **acumulado** |
| "PID X tiene una cola GFX" | **NO** | las colas (`userq`) no están en fdinfo; `amdgpu_ring_<name>` es por ring |

**Y la prohibition explícita**: `engine = 0` **no** implica "no usa GPU" (no-monotonía, S1).
Conversely `engine > 0` **sí** implica trabajo ejecutado belonging a ese cliente.

## 16 · MEMORY_ANALYSIS

Las cuatro claves son **por cliente** (S1). `drm-active-*` es un **subconjunto de `drm-resident-*`**.
El valor 0 de `drm-total` significa "no solicitó buffers", **no** "no está usando la GPU".
La doble contabilización estáSsí contemplada en la spec. **No hay ninguna clave de memoria por
proceso en fdinfo.**

## 17 · PROCESS_CLIENT_FD_ANALYSIS

```
1 proceso  --N-->  N FDs  --M-->  M drm_file  --1:1-->  M drm-client-id
   |                        |
   |                        +--> 1 drm_minor --> drm_device --> PCI BDF
   |
   +-- NO hay relacion directa con memoria, engines, VA space ni PASID
       en la superficie documentada de fdinfo
```

El proceso y el cliente DRM **no están unidos por ninguna clave**: se unen por el **path**
`/proc/<pid>/fd/<n>` más el `client_id` leído de ese mismo FD. `drm_file.pid` es la relación formal
en el kernel, pero **no es observable desde userspace** salvo por ese path.

## 18 · DRM_MASTER_ANALYSIS

`drm_master` es un concepto de **display ownership** (S2: *"The original DRM master of a device
'owns' the available drm resources"*, con leasing lessor/lessee). **No tiene relación con la
atribución de workloads GPU.** Además `drm_file.master` es **condicional**: *"Only relevant if
`drm_is_primary_client()` returns true"*, y los render nodes **no tienen master** (S2). En la RX550,
`card1` es primary y `renderD129` es render: **la mitad de nuestros clientes no tiene master**.

## 19 · CGROUP_ANALYSIS

`drmm_cgroup_register_region()` existe (S3): *"Register a region of a DRM device to cgroups"*. Es un
mecanismo de **atribución de recurso a cgroup**, es decir una **cuarta unidad**, distinta de
proceso, cliente y FD. **Su documentación no se obtuvo** (404) → semántica `NOT_ESTABLISHED`.
**No se incorpora a ningún criterio.**

## 20 · CONFLICT_MATRIX

| ID | A | B | Tipo | Capa | Estado |
|---|---|---|---|---|---|
| **Z-1** | `drm-client-id` = "1:1 con `struct drm_file`" (S1) | `client ID` = "el **GPU block** que causó el fault: TCP, SDMA, VCN…" (S4) | **Mismo término, objetos incompatibles** | `EXTERNAL_SPEC` vs `EXTERNAL_SPEC` | **`CONFLICT` NO RESUELTO** |
| **Z-2** | `drm_file` = estado por descriptor (S3); `drm_device.filelist` = "userspace **clients**" | `drm_master` agrupa "groups of **clients**" (S2) | Tres sentidos de "client" en la misma pila | `EXTERNAL_SPEC` | **`CONFLICT` NO RESUELTO** |
| **Z-3** | `pasid` incluido en `DRM_ATTRIBUTION_FIELDS` (A-2) | S4: `pasid` pertenece a `vmid ↔ PID` en un fault | **Campo de otra relación** | `AGENT_FORMALIZATION` vs `EXTERNAL_SPEC` | **RESUELTO: el proyecto usa un campo de otra relación** |
| **Z-4** | `drm-engine-*` "time spent busy" | "Values are **not required to be constantly monotonic**" | Acumulado vs actual | `EXTERNAL_SPEC` interno | **RESUELTO por la propia spec** |
| **Z-5** | "attributable" en `AGENTS.md:176` | 0 ocurrencias en 10 000+ líneas de doc DRM | Término sin semántica externa definida | `HUMAN_REQUIREMENT` vs `EXTERNAL_SPEC` | **`NOT_ESTABLISHED`** |

## 21 · PREVIOUS_CLAIMS_RECHECK

| PREVIOUS_CLAIM | NUEVA EVIDENCIA | STATUS | WHY | REPLACEMENT |
|---|---|---|---|---|
| "`pasid` es un campo de atribución de cliente DRM" (A-2, A-3) | S4: `pasid` enlaza **vmid ↔ system PID** durante un fault | **REFUTED** | pertenece a otra relación | "`pasid` es un identificador de espacio de direcciones, condicional a un fault" |
| "`pasid` obligatorio para nodos amdgpu" (`R1-DRM-FDS-ENUMERATED-FIX-RECORD:72-84`) | S4 | **REFUTED** | la fuente no lo sostiene | pendientes: no hay base para exigirlo |
| "La unidad de atribución es el FD" (A-1) | S1+S3: la unidad del `client_id` es el `drm_file` | **REFUTED** | FD ≠ `drm_file` cuando hay dup/shared | la unidad depende de la fila |
| "La cadena formal no está documentada" (`…-SEMANTICS`, antes) | S3 la documenta campo por campo | **REFUTADO / corregido** | ya corregido en V1 | — |
| "No hay definición de attribution en el kernel" | 0 ocurrencias en S1+S2+S3+S4+S5 | **CONFIRMADO** | — | — |
| `PASID_SEMANTICS = NOT_ESTABLISHED` | S4 define vmid↔PASID↔PID | **PARCIALMENTE REFUTADO** | ahora es `PARTIALLY_DEFINED` | — |

**Ningún documento anterior fue sobrescrito.**

## 22 · NEGATIVE_RESULTS

| Búsqueda | Resultado |
|---|---|
| `attribut*` en S1–S5 | **0** ocurraciones pertinentes |
| `pasid`/`VMID` en S1, S2, S3 | **0** |
| `amdgpu_gem_info`/`amdgpu_vm_info` en S1, S2, S3 | **0** — son driver-specific |
| `amdgpu` en S1, S2, S3 | **0** |
| Puente `gem_info` PID ↔ `drm-client-id` | **no documentado** |
| Definición de "using the GPU" | **no documentada** |
| Relación proceso→engine | **no documentada** |
| `dmem` cgroup | **404** |
| Código fuente amdgpu | **bot-wall ×2** |
| 4 búsquedas web | **0 resultados** |
| 5 herramientas de monitoreo | **no inspeccionadas** |

## 23 · UNKNOWN

`vmid` ↔ `PASID` fuera de un fault · "using the GPU" en `gem_info`/`vm_info` · varios `PASID` por
proceso · `PASID` compartido · `PASID` ↔ `drm_file` · lista de columnas de `gem_info`/`vm_info` ·
semántica de `dmem` cgroup · comportamiento de herramientas de monitoreo.

## 24 · NOT_ESTABLISHED

`PASID` como requisito de atribución · atribución de engine a proceso · atribución de memoria a
proceso por fdinfo · identidad de cliente por `pasid` ·Significado de "attributable" en terminología
externa.

## 25 · FALSIFICATION_CONDITIONS

| Afirmación | Falsificador |
|---|---|
| `PASID` no sirve para atribuir FDs | una fuente que documente `PASID ↔ drm_file` |
| No hay relación proceso→engine | una fuente que la defina formalmente |
| `drm-pdev` no es necesario para identidad de dispositivo | una fuente que mostrara que sysfs+BDF no basta (no hallada) |
| `drm-client-id` es opcional | S1 dejara de marcarlo optional |
| FD ≠ client | S1+S3 dejaran de implicar el mapeo 1:1 |
| "using the GPU" no está definido | S5 definiera el término |
| No hay definición externa de "attributable" | una fuente primaria que la contenga |

## 26 · FINAL_CLASSIFICATION

### `DEFINITION_PARTIALLY_ESTABLISHED`

**Justificación por lo establecido** (todas `DIRECT_DEFINITION`):
`process → drm_file.pid` · `drm_file → filp → FD` · `drm_file → minor → drm_device → PCI` ·
`drm_file ↔ drm-client-id` (1:1) · `drm_file.minor` = nodo · `drm-engine-*` por cliente y
acumulado · `drm-total/-shared/-resident/-active` por cliente · `vmid ↔ PASID ↔ PID` en fault ·
`ring ↔ actividad` por fences.

**Justificación por lo no establecido**:
el término "attributable" **no existe** en 10 000+ líneas de documentación DRM/AMDGPU · `pasid` no
pertenece a la relación de atribución de FDs · no hay relación proceso→engine · no hay definición de
"using the GPU" · no hay semántica de cgroup.

**Por qué no es `DEFINITION_ESTABLISHED`**: porque las *relaciones* están documentadas pero la
*definición del requisito* —qué de ellas debe contener una fila— no lo está, y dos de ellas
(`PASID`, `engine`) están condicional o acumuladas de forma que no sirven como predicado.

**Por qué no es `RESEARCH_INCOMPLETE`**: las 8 preguntas del criterio de calidad tienen respuesta
documentada o `NOT_ESTABLISHED` explícito. Lo que falta es *fuente*, y esa ausencia está
registrada.

## 27 · DECISION_NOT_MADE

**No se decide**: cuál de `any()`/`all()` es correcto para F-01 · si `pasid` debe salir de
`DRM_ATTRIBUTION_FIELDS` · cuál es la unidad de las filas de nodo · el nombre de `card_clients` · la
semántica de estado de ningún criterio.

**Motivo**: no existe definición externa de "attributable" que arbitre, y las dos alternativas de
F-01 usan campos que pertenecen a **relaciones distintas**.

## 28 · NEXT_RESEARCH_STEP

**Una sola acción**: obtener el código fuente de `amdgpu_vm_info` y `amdgpu_gem_info`
(`drivers/gpu/drm/amdgpu/amdgpu_vm_info.c`, `amdgpu_gem_info.c`) por una vía que no sea
`git.kernel.org` ni `elixir.bootlin.com` — p. ej. el paquete Debian `linux-source`, o un mirror de
código accesible — y determinar **qué columnas emite cada uno y si `vm_info` incluye `VMID`/`PASID`**.

Es el paso más discriminante porque resolvería los tres `UNKNOWN` de §23 que bloquean los criterios
**E (memoria)**, **G (VM/contexto)** y **H (PASID)**, y porque es la única vía que puede convertir
`"using the GPU"` de `NOT_ESTABLISHED` en una definición o en una negativa concluyente. Si el código
confirma que `vm_info` **no** expone `drm-client-id`, entonces la relación `PID ↔ cliente DRM` queda
**sin puente documentado**, y eso cierra por negación la vía de usar `gem_info`/`vm_info` como evidencia
de atribución de clientes.
