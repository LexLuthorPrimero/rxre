# R1-ATTRIBUTABLE-DEFINITION-RESEARCH-20260926

`DOCUMENT_KIND = RESEARCH`
`NORMATIVE_STATUS = RESEARCH_ONLY` — **no** es requisito, **no** es propuesta de requisito, **no**
está adoptado. No sustituye ni modifica `AGENTS.md`, ni
`R1-ATTRIBUTABLE-NODE-ROWS-REQUIREMENT-20260926.md`, que sigue `PROPOSED_NOT_ACTIVE`.
`CODE_CHANGED = NO` · `COLLECTOR_CHANGED = NO` · `TESTS_CHANGED = NO` · `AGENTS.md = UNCHANGED`
`HOST_MEASUREMENT = NONE` — toda evidencia de host usada aquí es **histórica y ya preservada**.
`COMMIT = NO`

> Este documento conserva matrices de referencia. **No declara qué significa "atribuible".**
> `ATRIBUIBLE = AMBIGUOUS` al cerrarse esta investigación.

---

## 1 · COBERTURA DE BÚSQUEDA

### 1.1 Universo local — barrido completo

Barrido sobre todo el repositorio (excluyendo `.git/`), por tipo de archivo.

| Término | `.md` | `.py` | `.json` |
|---|---|---|---|
| `attributable` | 8 | 5 | 3 |
| `attribution` | 20 | 9 | 5 |
| `DRM client` | 9 | 2 | 5 |
| `drm-client-id` | 9 | 4 | 2 |
| `drm-pdev` | 8 | 4 | 2 |
| `fdinfo` | 23 | 5 | 5 |
| `proc/*/fd` (patrón) | 21 | 6 | 13 |
| `class/drm` | 34 | 12 | 18 |
| `provenance` | 76 docs | — | — |
| **`attributable resource`** | **0** | 0 | 0 |
| **`attribution of file descriptor`** | **0** | 0 | 0 |
| **`ownership attribution`** | **0** | 0 | 0 |
| **`resource attribution`** | **0** | 0 | 0 |
| **`PCI device attribution`** | **0** | 0 | 0 |
| **`descriptor ownership`** | **0** | 0 | 0 |
| **`resource ownership`** | **0** | 0 | 0 |
| **`PASID process`** | **0** | 0 | 0 |
| `drm-usage-stats` | 1 | 0 | 0 |
| `drm_file` | 1 | 0 | 0 |

**Evidencia negativa resultante**: nueve conceptos del universo pedido **no tienen ninguna
ocurrencia** en el repositorio. No son terminología del proyecto. Donde el proyecto sí tiene
vocabulario fuerte es `provenance` (76 documentos) y `AGENTS.md` §Provenance discipline.

`drm-usage-stats` y `drm_file` aparecen una vez cada uno, y **ambos en el documento que esta misma
ronda anterior creó** — no en documentación preexistente.

### 1.2 Universo externo

| Fuente | Resultado |
|---|---|
| Kernel `drm-usage-stats` | **Obtenida** (7.3.0-rc4) |
| Kernel `drm-uapi` | **Obtenida** (7.3.0-rc4, 3630 líneas) |
| `man5 proc_pid_fd` | **Obtenida** (man-pages 6.19) |
| `man5 proc_pid_fdinfo` | **Obtenida** (man-pages 6.19) |
| `git.kernel.org` (cgit, fuente amdgpu) | **INACCESIBLE** — Anubis bot-wall |
| `elixir.bootlin.com` (fuente amdgpu) | **INACCESIBLE** — Anubis bot-wall |
| Búsquedas web para semántica de `pasid` | **2 intentos, 0 resultados** |

**Consecuencia**: la fuente primaria del *código* de amdgpu no se consultó. Todo lo relativo a
`pasid` queda en `NOT_ESTABLISHED`.

---

## 2 · MATRIZ DE FUENTES

### S1 · DRM client usage stats

| | |
|---|---|
| `SOURCE` | Kernel `Documentation/gpu/drm-usage-stats` |
| `URL` | `https://docs.kernel.org/gpu/drm-usage-stats.html` |
| `DATE_ACCESSED` | 2026-09-26 (versión mostrada **7.3.0-rc4**) |
| `AUTHORITY` | `EXTERNAL_SPEC` — documentación oficial del kernel, norma de la interfaz |
| `EXACT_SUBJECT` | Contenido de `/proc/<pid>/fdinfo/<fd>` para un FD DRM |
| `RELEVANT_PASSAGE` | Mandatory: `drm-driver`. Optional: `drm-pdev` ("For PCI devices this **should** contain the PCI slot address"); `drm-client-id` ("Unique value relating to the open DRM file descriptor used to **distinguish duplicated and shared file descriptors**… map 1:1 to… `struct drm_file`… Uniqueness… either globally unique, **or unique within the scope of each device, in which case `drm-pdev` shall be present as well**"). `pasid`: **ausente**. |
| `WHAT IT DEFINES` | Qué claves existen, cuáles son mandatory/optional, y qué significan `drm-pdev` y `drm-client-id` |
| `WHAT IT DOES NOT DEFINE` | No define "attributable". No define `pasid`. No define la relación proceso↔cliente. No lista amdgpu entre las implementaciones de driver específicas |
| `APPLICABILITY` | Directa: la RX550 es un dispositivo PCI con driver amdgpu y expone fdinfo |
| `LIMITATIONS` | `drm-pdev` y `drm-client-id` son **optional**: la spec no obliga a emitirlos |

### S2 · DRM Userland interfaces

| | |
|---|---|
| `SOURCE` | Kernel `Documentation/gpu/drm-uapi` |
| `URL` | `https://docs.kernel.org/gpu/drm-uapi.html` |
| `DATE_ACCESSED` | 2026-09-26 (7.3.0-rc4; 3630 líneas leídas) |
| `AUTHORITY` | `EXTERNAL_SPEC` |
| `EXACT_SUBJECT` | Vocabulario DRM: `drm_file`, `drm_master`, render nodes, *"owns"*, debugfs |
| `RELEVANT_PASSAGE` | `drm_ioctl_t` recibe `struct drm_file *file_priv` = *"DRM file this ioctl was made on"*. *"struct drm_master is used to track **groups of clients** with open primary device nodes. For every struct drm_file which has had at least once successfully become the device master… **All other clients have just a pointer to the drm_master** they are associated with."* Render nodes: *"drop the DRM-Master concept. There is no reason to associate render clients with a DRM-Master"*. Sobre *ownership*: *"The original DRM master of a device '**owns**' the available drm resources"*, y define `owner`/`lessor`/`lessee` **de `drm_master`**, en el contexto de *display resource leasing*. `drm_debugfs_gpuva_info()` vuelca *"the GPU VA mappings of a given DRM GPU VA manager"* (`drm_gpuvm`), por `drm_info_list` en **debugfs**. |
| `WHAT IT DEFINES` | Que un "cliente DRM" ≈ `drm_file`; que clients se agrupan por master; que el notion de *ownership* del kernel es sobre `drm_master` y recursos de display, **no** sobre FDs ni clients; que el espacio de direcciones GPU se expone por **debugfs**, no por fdinfo |
| `WHAT IT DOES NOT DEFINE` | **`pasid`: 0 ocurrencias en 3630 líneas.** `attribut*`: 1 ocurrencia, y es *"Common trace events attributes"* — no attributable. `ownership`: 0 ocurrencias. |
| `APPLICABILITY` | Directa para vocabulario; el leasing no aplica a la RX550 como objeto de estudio |
| `LIMITATIONS` | No es una especificación de atribución; es UAPI general |

### S3 · `proc_pid_fd(5)`

| | |
|---|---|
| `SOURCE` | `man5 proc_pid_fd`, Linux man-pages **6.19** (página 2026-02-08; HTML 2026-09-09), autor Michael Kerrisk |
| `URL` | `https://man7.org/linux/man-pages/man5/proc_pid_fd.5.html` |
| `DATE_ACCESSED` | 2026-09-26 |
| `AUTHORITY` | `EXTERNAL_DOCUMENTATION` — UAPI primaria documentada por el proyecto man-pages |
| `RELEVANT_PASSAGE` | *"one entry for each file which the process has open, named by its file descriptor, and which is a symbolic link to the actual file"*. *"Permission to dereference or read (readlink(2)) the symbolic links in this directory is governed by a **ptrace access mode PTRACE_MODE_READ_FSCREDS** check"*. *"those inodes still have permission bits and **ownership information distinct from those of the /proc/pid/fd entry, and that the owner may differ from the user and group IDs of the process**"*. *"In a multithreaded process, the contents of this directory are not available if the main thread has already terminated"* |
| `WHAT IT DEFINES` | La relación FD→fichero (por symlink) y **el modelo de autorización de esa lectura** |
| `WHAT IT DOES NOT DEFINE` | No define "atribuible". No define relación con cliente DRM |
| `APPLICABILITY` | Directa: es la lectura que hace `scan_fds()` |
| `LIMITATIONS` | `PTRACE_MODE_READ_FSCREDS` implica que la denegación depende de relación uid/privilegio, no solo de DAC |

### S4 · `proc_pid_fdinfo(5)`

| | |
|---|---|
| `SOURCE` | `man5 proc_pid_fdinfo`, man-pages **6.19** (página 2026-07-18; HTML 2026-09-09) |
| `URL` | `https://man7.org/linux/man-pages/man5/proc_pid_fdinfo.5.html` |
| `DATE_ACCESSED` | 2026-09-26 |
| `AUTHORITY` | `EXTERNAL_DOCUMENTATION` |
| `RELEVANT_PASSAGE` | *"The files in this directory are **readable only by the owner of the process**."* *"The content depends on the type of file referred to by the corresponding file descriptor."* Los tipos documentados son: regular files/directories, `eventfd`, `epoll`, `signalfd`, `inotify`, `fanotify`, `timerfd`. |
| `WHAT IT DEFINES` | Que fdinfo tiene **otro** modelo de autorización que `/proc/pid/fd`; y el contenido para 7 tipos de fichero |
| `WHAT IT DOES NOT DEFINE` | **No documenta el fdinfo de un FD DRM.** No menciona `drm-client-id`, `drm-pdev`, `pasid` ni `drm-driver` |
| `APPLICABILITY` | Directa por la diferencia de permisos; el contenido DRM queda solo en S1 |
| `LIMITATIONS` | La omisión de DRM en esta página hace que el fdinfo DRM sea **extensión de driver**, y su única norma sea S1 |

### S5 · Requisito humano del proyecto

| | |
|---|---|
| `SOURCE` | `AGENTS.md` §Ownership `:176-179`; §Evidence; §Provenance discipline `:98-107`; `:32` |
| `AUTHORITY` | `HUMAN_REQUIREMENT` |
| `RELEVANT_PASSAGE` | §Ownership: *"complete attributable evidence for the RX550's card and render nodes, identified by PCI identity rather than by node name, plus user/root namespaces, **DRM FDs**, writers…"*. `:103-104` (ejemplo de procedencia): *"**Requirement: attribute DRM clients per process.** Formalisation: the row `clients_pasid_attributable`."* `:32`: *"Identify a device by PCI identity, never by its `cardN` name"* |
| `WHAT IT DEFINES` | Los dos nodos; la identidad por PCI; que "DRM FDs" es un ítem **distinto** de los nodos; y un **ejemplo** cuyo requisito es "attribute DRM clients per process" |
| `WHAT IT DOES NOT DEFINE` | Ninguna clave. Ninguna unidad para *attributable*. Ningún umbral |
| `LIMITATIONS` | `:103-104` es un **ejemplo** de disciplina de procedencia, no el requisito de esta investigación. Su fuerza normativa para nosotros es `UNKNOWN` |

### S6 · Evidencia de host preservada — Pass A sin privilegios

| | |
|---|---|
| `SOURCE` | `01-AUDITORIA/OWNERSHIP-AUDIT-HOST-C/OWNERSHIP-AUDIT-HOST-C-20250925T231635Z.md:55-70`, `:60` |
| `DATE` | 2025-09-25T23:16:35Z |
| `AUTHORITY` | `OBSERVED_HOST_EVIDENCE` |
| `RELEVANT_PASSAGE` | `| 1923 | Xwayland | 1000 | 1825 | 13 | 71 | 0000:01:00.0 | **43** | 0 KiB | 2184 KiB |` — "Clientes legibles: **1**" sobre `card1`; sobre `renderD129` "Clientes legibles: **0**… el compositor activo tiene `/proc` ilegible". `:60`: *"`/sys/kernel/debug/dri/1/clients` — No hay attribution de kernel-level (**PASID→PID**) — `NOT_AVAILABLE`"* |
| `WHAT IT DEFINES` | El **único valor `pasid` preservado** en el proyecto: `43`. Y que `client-id 71` con `pdev 0000:01:00.0` pertenece al FD 13 de Xwayland |
| `WHAT IT DOES NOT DEFINE` | El significado de `43`. Nada sobre `pasid` en general |
| `LIMITATIONS` | **Un solo FD, sin privilegios, de un host y una fecha.** No hay fdinfo crudo preservado (§3) |

### S7 · Evidencia de host preservada — corrida privilegiada R1

| | |
|---|---|
| `SOURCE` | `01-AUDITORIA/R1-C1-CORRECTION-CLOSURE-20260926.md:321-384` |
| `DATE` | 2026-09-26 |
| `AUTHORITY` | `OBSERVED_HOST_EVIDENCE` |
| `RELEVANT_PASSAGE` | `drm_fds_found` 12; `drm-client-id`/`drm-pdev`/`pasid` = **12/12/12**. 4 procesos: systemd(1), systemd-logind(993), kwin_wayland(1825, *cinco en card1 y cuatro en renderD129*), Xwayland(1923). `debugfs clients` (minor 129, 715 B, 4 filas) con columnas `command tgid dev master a uid magic name id`; kwin_wayland con **ids 47, 65, 71**. *"Neither `pasid` nor `drm-client-id` is engine state."* *"The sweep (~02:37) and the `clients` read (02:42) are different windows, in which ids may be reassigned. **No mapping is asserted.**"* Proceso→engine: `NOT_AVAILABLE` |
| `WHAT IT DEFINES` | Que 1 proceso puede tener 9 FDs y 3 ids de cliente distintos. Que `pasid` y `drm-client-id` no son estado de motor |
| `WHAT IT DOES NOT DEFINE` | Correspondencia `drm-client-id` ↔ `clients.id` |
| `LIMITATIONS` | Agregados, no per-FD. El `12/12/12` son **contadores**, no texto |

### S8 · Fuentes intentadas y no obtenidas

| Fuente | URL | Resultado |
|---|---|---|
| Linux kernel cgit (amdgpu) | `git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/drivers/gpu/drm/amdgpu/amdgpu_fdinfo.c` | `INACCESS` — Anubis bot-wall |
| elixir.bootlin | `elixir.bootlin.com/linux/latest/source/drivers/gpu/drm/amdgpu/amdgpu_fdinfo.c` | `INACCESS` — Anubis bot-wall |
| Búsquedas web | 2 intentos | 0 resultados |

---

## 3 · HALLAZGO DE EVIDENCIA: NO HAY fdinfo CRUDO PRESERVADO

Barrido de los 6 bundles (`R1-*.json`, `C1-PREFLIGHT-*.json`) buscando cualquier `fdinfo` con texto no vacío:
**0 ocurrencias en los 6**.

Consecuencia: el `12/12/12` de S7 **no es re-verificable** desde evidencia preservada. Es
`OBSERVED` en el momento de la recolección; el texto que lo sustentaba no se conservó. La única
excepción es S6, un valor de `pasid` transcrito a mano en una tabla Markdown.

`REPRODUCIBILITY` de cualquier definición que dependa de esos contadores es **`LOW`** mientras el
fdinfo crudo no se preserve.

---

## 4 · MATRIZ DE DEFINICIONES

`PROVENANCE` de cada una. Ninguna tiene `HUMAN_REQUIREMENT` salvo donde se indica.

### D1 · Atribución por proceso

| | |
|---|---|
| `DEFINITION` | Un FD es atribuible si se puede establecer a qué proceso pertenece |
| `UNIT` | descriptor |
| `REQUIRED_EVIDENCE` | El path `/proc/<pid>/fd/<n>` legible y el `readlink` resuelto |
| `OPTIONAL_EVIDENCE` | uid, ppid, comm, cmdline |
| `MINIMUM_PROOF` | `os.listdir` del directorio + `os.readlink` sin excepción |
| `WHAT IT PROVES` | La relación **proceso→FD** (S3) |
| `WHAT IT DOES NOT PROVE` | Nada sobre el nodo, el cliente, ni el dispositivo |
| `FALSE_POSITIVE_RISK` | Bajo: un FD enumerable pertenece al proceso. **El riesgo es de universo, no de identidad** |
| `FALSE_NEGATIVE_RISK` | Bajo: no exige campos opcionales |
| `OBSERVABILITY` | `HIGH` — es la lectura que el collector ya hace |
| `DEPENDENCIES` | `PTRACE_MODE_READ_FSCREDS` (S3) |
| `PRIMARY-SOURCE_SUPPORT` | **S3**, textual |
| `PROJECT-RELEVANCE` | Parcial: `AGENTS.md` no nombra proceso como unidad de *attributable*. El ejemplo `:103` dice "per process" para una *otra* fila |
| `FALSIFICATION` | Refutada si S3 mostrara que la entrada de `/proc/pid/fd` no pertenece al proceso. No lo muestra |
| `PROVENANCE` | `EXTERNAL_SOURCE` (S3) + `AGENT_FORMALIZATION` (la fila) |
| `STATUS` | `PARTIALLY_DEFINED` |

### D2 · Atribución por FD al nodo

| | |
|---|---|
| `DEFINITION` | Un FD es atribuible si su symlink resuelve a un nodo DRM auditado |
| `UNIT` | descriptor |
| `REQUIRED_EVIDENCE` | `readlink` → `/dev/dri/{card,render}N` |
| `MINIMUM_PROOF` | El target del symlink está en el conjunto de nodos probados |
| `WHAT IT PROVES` | FD→**nodo**, y por tanto FD→dispositivo (el nodo pertenece a un dispositivo) |
| `WHAT IT DOES NOT PROVE` | Nada sobre cliente, ni sobre el **proceso** más allá de la ruta del path |
| `FALSE_POSITIVE_RISK` | **El núcleo**: el target es un *nombre* (`card1`), y `AGENTS.md:32` prohíbe identificar por nombre |
| `FALSE_NEGATIVE_RISK` | Nulo |
| `OBSERVABILITY` | `HIGH` |
| `PRIMARY-SOURCE_SUPPORT` | **S3**, para el symlink; **S5** (`AGENTS.md:32`) para la prohibición de nombres |
| `FALSIFICATION` | Refutada si `AGENTS.md:32` o `:176` no existieran. Existen |
| `PROVENANCE` | `EXTERNAL_SOURCE` (S3) |
| `STATUS` | `PARTIALLY_DEFINED` — y **contradiche `AGENTS.md:32` si se toma sola** |

### D3 · FD + nodo por identidad PCI

| | |
|---|---|
| `DEFINITION` | Un FD es atribuible si su nodo está probado por PCI (BDF + driver) y no por nombre |
| `UNIT` | descriptor |
| `REQUIRED_EVIDENCE` | `GPU_PCI_TARGET` verificado (vendor/device/BDF/class/**driver=amdgpu**), nodos derivados de sysfs, y el target del symlink pertenecer a ese conjunto |
| `OPTIONAL_EVIDENCE` | `drm-pdev` (**optional** en S1) |
| `MINIMUM_PROOF` | `PCI_IDENTITY_STATUS=PROVEN` ∧ `DRM_DISCOVERY_STATUS=PROVEN` ∧ target ∈ nodos |
| `WHAT IT PROVES` | FD→nodo→**dispositivo PCI**, por identidad y no por nombre. Es lo que `AGENTS.md:32` y `:176` piden literalmente |
| `WHAT IT DOES NOT PROVE` | Nada sobre el cliente DRM. Ni que el FD no sea un duplicado de otro |
| `FALSE_POSITIVE_RISK` | Bajo |
| `FALSE_NEGATIVE_RISK` | Nulo: no depende de ningún campo de fdinfo |
| `OBSERVABILITY` | `HIGH` — ya implementado, y `gpu_proven` implica nodo amdgpu |
| `PRIMARY-SOURCE_SUPPORT` | **S5** (`HUMAN_REQUIREMENT`, textual) + **S1** para `drm-pdev` como opcional |
| `PROJECT-RELEVANCE` | **Alta**: es la única definición que satisface literalmente `AGENTS.md:32` y `:176` |
| `FALSIFICATION` | Refutada si una fuente primaria demonstrara que la asociación PCI **no es necesaria** para establecer FD→nodo. S1 no lo dice; y `AGENTS.md:32` la **exige** |
| `PROVENANCE` | `HUMAN_REQUIREMENT` (S5) + `EXTERNAL_SOURCE` (S1, para lo opcional) |
| `STATUS` | `PARTIALLY_DEFINED` |

### D4 · FD + DRM client

| | |
|---|---|
| `DEFINITION` | Un FD es atribuible si puede distinguirse de otros FDs si representa el mismo `drm_file` o uno distinto |
| `UNIT` | descriptor |
| `REQUIRED_EVIDENCE` | `drm-client-id` presente y legible (**optional** en S1) |
| `OPTIONAL_EVIDENCE` | `drm-pdev`, que acota el alcance del id |
| `MINIMUM_PROOF` | El texto leído contiene `drm-client-id:` |
| `WHAT IT PROVES` | La relación **FD↔cliente DRM**, en el sentido de S1: distinguir FDs duplicados y compartidos |
| `WHAT IT DOES NOT PROVE` | El proceso (el id no lo dice). El nodo. La actividad |
| `FALSE_POSITIVE_RISK` | Medio: la presencia de la clave no valida que el valor sea coherente con el nodo que se audita — S1 no exige igualdad, y el collector **no la comprueba** |
| `FALSE_NEGATIVE_RISK` | Medio: `drm-client-id` es **optional** en la spec; un driver conforme puede no emitirlo |
| `OBSERVABILITY` | `MEDIUM` — se observó 12/12, pero **no hay texto crudo preservado** (§3) |
| `PRIMARY-SOURCE_SUPPORT` | **S1**, textual y fuerte ("distinguish duplicated and shared file descriptors") |
| `PROJECT-RELEVANCE` | Alta si se adopta la lectura de `:103-104` ("attribute DRM clients per process") |
| `FALSIFICATION` | Refutada si S1 no definiera `drm-client-id`. Sí lo define |
| `PROVENANCE` | `EXTERNAL_SOURCE` (S1) |
| `STATUS` | `PARTIALLY_DEFINED` |

### D5 · Proceso + DRM client

| | |
|---|---|
| `DEFINITION` | Un FD es atribuible si su proceso se conoce **y** su cliente DRM se distingue |
| `UNIT` | descriptor, con dos relaciones |
| `REQUIRED_EVIDENCE` | D1 ∧ D4 |
| `MINIMUM_PROOF` | Path legible + `drm-client-id` presente |
| `WHAT IT PROVES` | La cadena **proceso→FD→cliente**, que es literalmente el ejemplo de `AGENTS.md:103` |
| `WHAT IT DOES NOT PROVE` | El nodo. La relación cliente→dispositivo |
| `FALSE_POSITIVE_RISK` | Bajo |
| `FALSE_NEGATIVE_RISK` | **El más alto**: hereda los dos. El `:103` es un ejemplo, no el requisito de esta fila, así que exigir ambas cosas puede exceder el requisito |
| `OBSERVABILITY` | `MEDIUM` (misma limitación de §3) |
| `PRIMARY-SOURCE_SUPPORT` | S1 para la relación cliente; S3 para la relación proceso. **La composición no tiene fuente**: es `INFERENCE` |
| `PROJECT-RELEVANCE` | Alta si el ejemplo `:103` se toma como precedente |
| `FALSIFICATION` | Refutada si `AGENTS.md:103-104` se declarara no normativa. Es un ejemplo dentro de §Provenance discipline, y su fuerza es `UNKNOWN` |
| `PROVENANCE` | `INFERENCE` (composición) sobre `EXTERNAL_SOURCE` (cada relación) |
| `STATUS` | `AMBIGUOUS` |

### D6 · Incluyendo PASID

| | |
|---|---|
| `DEFINITION` | D4 ∧ presencia de `pasid` |
| `UNIT` | descriptor |
| `REQUIRED_EVIDENCE` | `drm-client-id` **y** `pasid` |
| `MINIMUM_PROOF` | Ambas claves presentes en el texto leído |
| `WHAT IT PROVES` | Lo de D4, más la presencia de un campo que **no tiene definición primaria localizada** |
| `WHAT IT DOES NOT PROVE` | Nada verificable sobre PASID. `S2` expone el espacio de direcciones GPU por **debugfs** (`drm_gpuvm`), no por fdinfo; y `S1` no lista `pasid` |
| `FALSE_POSITIVE_RISK` | Desconocido: no se puede evaluar una propiedad no definida |
| `FALSE_NEGATIVE_RISK` | **Alto y no cuantificable**: se puede exigir un campo cuya semántica_required es `NOT_ESTABLISHED` |
| `OBSERVABILITY` | `MEDIUM` — observado 12/12 (S7) y un valor `43` (S6), sin texto preservado |
| `DEPENDENCIES` | **amdgpu-específico**: `pasid` no está en S1, y S1 exige prefijo `drm-` o `driver_name-`; `pasid` no tiene ninguno |
| `PRIMARY-SOURCE_SUPPORT` | **NINGUNA** — 0 ocurrencias en S1 y en las 3630 líneas de S2 |
| `PROJECT-RELEVANCE` | No establecida. El propio proyecto ya registró `PASID→PID` como `NOT_AVAILABLE` (S6 `:60`) |
| `FALSIFICATION` | Refutada si una fuente primaria definiera `pasid` como requisito de atribución. No se localizó ninguna |
| `PROVENANCE` | `AGENT_FORMALIZATION` (`DRM_ATTRIBUTION_FIELDS`, `R1-DRM-FDS-ENUMERATED-FIX-RECORD:72-84`) |
| `STATUS` | **`NOT_ESTABLISHED`** |

### D7 · Conjunción de dos relaciones (FD→nodo PCI ∧ FD→cliente)

| | |
|---|---|
| `DEFINITION` | Un FD es atribuible si se puede establecer su asociación al nodo por identidad PCI **y** distinguir su cliente DRM |
| `UNIT` | descriptor |
| `REQUIRED_EVIDENCE` | D3 ∧ D4 |
| `MINIMUM_PROOF` | `gpu_proven` ∧ target ∈ nodos ∧ `drm-client-id` presente |
| `WHAT IT PROVES` | La cadena **proceso→FD→{nodo→dispositivo PCI, cliente DRM}** |
| `WHAT IT DOES NOT PROVE` | Unicidad global del id; coherencia entre `drm-pdev` y el nodo auditado; actividad |
| `FALSE_POSITIVE_RISK` | El más bajo de la familia: exige dos relaciones independientes |
| `FALSE_NEGATIVE_RISK` | Medio-alto: depende de un campo **optional** en S1 |
| `OBSERVABILITY` | `MEDIUM` |
| `PRIMARY-SOURCE_SUPPORT` | Cada mitad por separado (S1, S3, S5). **La conjunción no tiene fuente** |
| `PROJECT-RELEVANCE` | Es la lectura más literal de `AGENTS.md:176-179` + `:32` **y** de `:103-104` |
| `FALSIFICATION` | Refutada si `AGENTS.md:103-104` resultara no normativo **y** `:176` no exigiera la relación cliente. `:176` no la exige explícitamente → el falsificador **parcialmente aplica** |
| `PROVENANCE` | `INFERENCE` |
| `STATUS` | `AMBIGUOUS` |

### D8 · Atribución por recurso GPU

Aparece en el universo pedido y en `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md:87` ("VRAM/GTT"). Se
registra como definición **no aplicable**: la atribución de recurso GPU (VRAM, GTT) es una
magnitud **por cliente**, no por descriptor, y la relación cliente↔memoria no tiene fuente primaria
localizada para el requisito actual. `STATUS = NOT_ESTABLISHED`. No se desarrolla.

---

## 5 · MATRIZ DE CONFLICTOS

| ID | SOURCE_A | CLAIM_A | SOURCE_B | CLAIM_B | TIPO | CAPA | ESTADO |
|---|---|---|---|---|---|---|---|
| X-1 | `R1-DRM-FDS-ENUMERATED-FIX-RECORD-20260926.md:72-84` | `pasid` es requerido porque `gpu_proven` prueba nodo amdgpu | S1 + S2 | `pasid` no está en la spec DRM; 0 ocurrencias en 3630 líneas de `drm-uapi` | Fuente primaria ausente vs afirmación de proyecto | `AGENT_FORMALIZATION` vs `EXTERNAL_SPEC` | **`UNRESOLVED`** — la fuente primaria no se pudo consultar (S8) |
| X-2 | `AGENTS.md:176` | "complete attributable evidence" para los nodos | `AGENTS.md:176-178` | "DRM FDs" es un ítem **distinto** de la lista | Requisito que enumera un ítem que la fila de nodo también asume | `HUMAN_REQUIREMENT` interno | **`UNRESOLVED`** — requiere decisión humana |
| X-3 | `AGENTS.md:103-104` | Requisito de ejemplo: "attribute DRM clients **per process**" | `AGENTS.md:176` | No nombra proceso ni cliente | Dos enunciados del mismo documento normativo con alcances distintos | `HUMAN_REQUIREMENT` interno | **`UNRESOLVED`** — `:103` es ejemplo, no requisito |
| X-4 | S2 (leasing) | El kernel define "owns/ownership" sobre `drm_master` y recursos de display | Nombre del proyecto | "ownership" se usa para FDs/clientes | Vocabulario homónimo con objetos distintos | `EXTERNAL_SPEC` vs `AGENT_FORMALIZATION` | **`UNRESOLVED`** — el proyecto no importó el término del kernel |
| X-5 | `OWNERSHIP-AUDIT-HOST-C-20250925T231635Z.md:60` (2025-09-25) | `client-id 71` en FD 13 de Xwayland | `R1-C1-CORRECTION-CLOSURE-20260926.md:363-368` (2026-09-26) | `id 71` en una fila de `kwin_wayland` | **NO ES CONFLICTO**: fechas y ventanas distintas | `OBSERVED_HOST_EVIDENCE` | **`NOT_COMPARABLE`** — registrado para que nadie lo promueva a conflicto |

---

## 6 · MATRIZ DE FALSIFICACIÓN

| Definición | Falsificador concreto | Estado |
|---|---|---|
| D1 | S3 mostrara que la entrada de `/proc/pid/fd` no pertenece al proceso | no ocurrió |
| D2 | `AGENTS.md:32` no existiera | no ocurrió |
| D3 | Una fuente primaria mostrara que la identidad PCI **no es necesaria** para FD→nodo | no ocurrió; y `AGENTS.md:32` la exige |
| D4 | S1 no definiera `drm-client-id` | no ocurrió |
| D5 | `AGENTS.md:103-104` resultara no normativo | **no evaluable** — depende de una decisión sobre el valor del ejemplo |
| D6 | Una fuente primaria definiera `pasid` como requisito de atribución | **no se localizó ninguna**; la fuente de código es inaccesible (S8) |
| D7 | `AGENTS.md:176` no exigiera la relación cliente **y** `:103` no fuera normativo | `:176` no la exige → falsificador **parcialmente aplica** |
| D8 | Una fuente primaria definiera la relación cliente↔memoria como parte del requisito actual | no se localizó |

Ningún falsificador es circular: ninguno se apoya en el comportamiento actual del collector.

---

## 7 · LO QUE ESTA INVESTIGACIÓN NO CIERRA

`ATRIBUIBLE = AMBIGUOUS`

No se cierra porque:

1. `HUMAN_REQUIREMENT` no enumera información, campos, ni unidad. `:176-179` y `:103-104` son
   ambos compatibles con definiciones distintas y no se concilian.
2. La única fuente primaria que define campos de atribución (S1) hace **optional** los dos que
   importan, y **no contiene** el tercero.
3. El concepto "attributable" **no aparece** en la documentación DRM del kernel: 0 en
   `drm-usage-stats`, 1 en 3630 líneas de `drm-uapi` y es *"trace events attributes"*.
4. La fuente primaria del código de amdgpu no fue consultable (S8), así que
   `PASID_SEMANTICS = NOT_ESTABLISHED` no es una conclusión provisional: es un hueco real.
5. El fdinfo crudo **no está preservado** en ningún bundle (§3), así que ninguna definición que
   dependa de esos campos es re-verificable hoy.

Lo que sí queda establecido, y no depende de lo anterior:

- FD ≠ cliente DRM ≠ proceso ≠ nodo, por S1 y S2, con evidencia de host en S6/S7.
- `/proc/pid/fd` y `/proc/pid/fdinfo` tienen **modelos de autorización distintos** (S3 vs S4), lo
  que hace que "FD legible" y "fdinfo legible" sean hechos independientes.
- El *ownership* en vocabulario DRM del kernel es sobre `drm_master` y recursos de display (S2), no
  sobre FDs ni clientes.
- `PASID→PID` ya fue registrado como `NOT_AVAILABLE` por el propio proyecto (S6 `:60`).
