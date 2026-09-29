# R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926

`DOCUMENT_KIND` = `REQUIREMENT_REPAIR` + `TECHNICAL_SPEC` · `NORMATIVE_STATUS` = `RESEARCH_ONLY`
Reparación del requisito humano. **No** es una decisión normativa del proyecto.
`CODE_CHANGE_ALLOWED` = `NO` · nada implementado, commiteado ni ejecutado.
`PROJECT_MAPPING` = **`NOT_ATTEMPTED`** (§5). Token unificado 2026-09-26: antes decía
`DEFERRED_PENDING_SPEC_CLOSURE`, que significaba lo mismo pero no coincidía con el
resto de la documentación vigente.

Base: `R1-TECHNICAL-SEMANTIC-MODEL-v3-20260926.md` (`TECHNICAL_MODEL_STATUS = CLOSED`).
No se re-deriva ninguna fuente; no se busca ninguna intención humana alguna.

---

## 1 · `HUMAN_REQUIREMENT_STATUS = HUMAN_REQUIREMENT_DEFECT · RESOLVED_BY_DECOMPOSITION`

**Reclasificado.** La pregunta «¿qué quiso decir el humano con *attributable*?» **no es una
incógnita técnica pendiente**: es un defecto de especificación, y su corrección fue la
descomposición de §2. No se reintenta. La分类 `DEFECTIVE_COMPOSITE_REQUIREMENT` queda como
histórico de esta misma sección.

### 1.0 · `ORIGINAL_STATUS = DEFECTIVE_COMPOSITE_REQUIREMENT` (histórico)

**Texto humano, conservado sin alterar** (`AGENTS.md:176-177`):

> "`FULL` requires complete attributable evidence for the RX550's card and render nodes,
> identified by PCI identity rather than by node name"

**Texto humano previo** (`54b3ea8`): *"`OWNERSHIP=FULL` requires complete, attributable evidence
for `card1`, `renderD129`, user/root namespaces, DRM FDs, writers, agents, PM, governor, IRQ,
scheduler, read-ahead, storage, Btrfs, guard, and restore"*.

### 1.1 Qué mezclaba exactamente

Un único sintagma — *"complete attributable evidence"* — gluten **al menos ocho** conceptos técnicos
de unidades, fuentes y relaciones distintas:

| # | Concepto mezclado | Unidad real | Por qué no puede seguir unido |
|---|---|---|---|
| 1 | completitud de la tabla de descriptores | proceso / descriptor | sysfs+`/proc`, sin fdinfo |
| 2 | identidad del dispositivo | nodo (`drm_minor`) | `drm_device`+PCI, sin fdinfo |
| 3 | identidad del fichero/cliente DRM | `drm_file` | `drm-client-id`, 1:1 por construcción; **unicidad** según spec, **sin estabilidad prometida** |
| 4 | asociación con el proceso | par (`drm_file`, instante) | `drm_file.pid`, **mutable** |
| 5 | memoria del cliente | agregado por `drm_file` | `drm_print_memory_stats`, **por driver** |
| 6 | actividad de engine | `drm_file` × engine | `drm-engine-*`, **acumulada, no monótona** |
| 7 | VM/PASID | vmid | **fuente primaria inaccesible** |
| 8 | *client-id* de page fault | bloque de hardware | **entidad distinta**, nombre colisionante |

**El defecto es estructural, no de redacción**: los cuatro primeros tienen **fuentes distintas**
(`/proc`, sysfs, `fdinfo`, `fdinfo`), los cuatro últimos **no son siquiera entidades del mismo
dominio**. "Atribuible" no tenía unidad.

### 1.2 Semántica humana explícita que se conserva

Se recupera todo lo que el texto sí determina: (a) la exigencia de **completitud**; (b) el ámbito
**card y render nodes**; (c) el método de identificación **PCI identity, not node name**
(`AGENTS.md:177` y `:32`); (d) la cláusula de fallo *"If FD visibility is incomplete… `OWNERSHIP !=
FULL`"* (`:180-181`); (e) *"a client is active"* (`:180-181`), conservado como **texto humano** y
**no** convertido en propiedad, porque no se sabe si "active" califica cliente DRM, proceso o
cualquiera.

### 1.3 Lo que se declara no recuperable

Que "attributable" designara un objeto determinado. **No se reintenta.** Se registra
`NOT_ESTABLISHED` y se sigue. La reparación de §1.1 **no depende** de recuperarlo: las ocho
propiedades se justifican por fuentes del kernel, no por intención.

---

## 2 · `REPAIRED_TECHNICAL_REQUIREMENTS`

Ocho propiedades. **Ninguna contiene a otra.** No se crea `DRM_ATTRIBUTION_FIELDS`, ni
`ATTRIBUTABLE`, ni `CLIENT_PROCESS_ASSOCIATION`, ni bolsa de campos con `any()`/`all()`.

> **Nota sobre los nombres.** Cada nombre nombra **la relación que representa**, no un tema. Ninguno
> afirma que la propiedad esté exigida por el proyecto: son propiedades técnicas definidas aquí.
> `DRM_CLIENT_*` nombra la **unidad** (`drm_file`), no una exigencia. `DRM_FILE_CLIENT_IDENTITY` no se
> renombra a `DRM_CLIENT_IDENTITY` porque el modelo establece (`C-2`) que *client* colisiona con al
> menos tres entidades; la unidad demostrada es `drm_file`.

---

### `RT-1` · `NODE_COMPLETENESS`

- `ENTITY / PROPERTY`: `NODE_COMPLETENESS` — visibilidad del nodo y cobertura de la tabla de FDs/procesos.
- `DEFINITION`: el nodo existe y fue probado como el nodo DRM de la RX550; y para cada proceso del
  universo barrido, su tabla de descriptores pudo enumerarse y cada descriptor quedó resuelto.
- `UNIT`: **proceso** (agregado) y **descriptor** (individual). No cliente, no `drm_file`.
- `SOURCE`: `proc_pid_fd(5)`; sysfs para la existencia del nodo. **Ninguna clave de fdinfo.**
- `RELATION`: proceso → tabla de FDs; descriptor → symlink resuelto.
- `CARDINALITY`: 1 proceso → N descriptores.
- `LIFETIME`: la del proceso en el instante del barrido.
- `MUTABILITY`: el universo cambia entre barridos; la cobertura es **histórica**.
- `OBSERVABILITY`: `EXPOSED`+`READABLE`+`OBSERVED`. El único límite: "no existe" e "ilegible" no
  se distinguen desde el symlink.
- `WHAT_IT_PROVES`: que la lectura fue completa **en esa ventana**.
- `WHAT_IT_DOES_NOT_PROVE`: nada sobre `drm_file`, `drm-client-id`, `drm-pdev`, memoria, engine o
  PASID. **No** es identidad de cliente.
- `FALSIFIER`: un descriptor sin resolver que no degradara la completitud; o un `readlink` fallido
  reportado como descriptor inexistente.
- `CURRENT_STATE`: `HOST-C` — pasada A: 4 PID con `FD_UNREADABLE_NO_PRIVILEGE`; pasada ampliada bajo
  privilegio: **12 FDs** leídos, `fd_absence_proven_pids = 0`, 1 PID desvanecido con target no
  resoluble. `TEMPORALITY = 2025-09-25T23:16:35Z` / cierre 2026-09-26, **pre-C1**; ningún artefacto
  de la matriz de ownership de este host fue producido por el collector actual.
- `PROVENANCE`: `HUMAN_REQUIREMENT` (completitud) + `PRIMARY_KERNEL_SOURCE` (semántica) +
  `AGENT_FORMALIZATION` (formalización previa de las filas).

### `RT-2` · `DRM_NODE_PCI_IDENTITY`

- `ENTITY / PROPERTY`: `DRM_NODE_PCI_IDENTITY` — el nodo pertenece al dispositivo PCI de la RX550.
- `DEFINITION`: el `drm_minor` observado resuelve a un `drm_device` cuyo `struct device` es el
  dispositivo PCIe objetivo, identificado por BDF, `vendor`, `device`, `class` y driver.
- `UNIT`: **nodo** (`drm_minor`).
- `SOURCE`: sysfs (`GPU_PCI_TARGET`); `minor->dev`; rama `dev_is_pci`. **No requiere fdinfo.**
- `RELATION`: `drm_minor` → `drm_device` → PCI device. `drm-pdev` es un **BDF** derivado, no
  suficiente por sí solo.
- `CARDINALITY`: 1 `drm_device` → N minors; 1 minor → 1:0:1 dispositivo PCI.
- `LIFETIME`: la del `drm_device`.
- `MUTABILITY`: inmutable tras el probe.
- `OBSERVABILITY`: `EXPOSED`+`READABLE` sin leer un solo byte de `/proc/*/fdinfo`.
- `WHAT_IT_PROVES`: que el nodo pertenece al dispositivo correcto.
- `WHAT_IT_DOES_NOT_PROVE`: **nada sobre clientes.** `drm-pdev` es **constante por dispositivo** y
  **no discrimina** `drm_file`; y no transporta `vendor`/`device`/`class`. `cardN` **no** es
  identidad de dispositivo.
- `FALSIFIER`: un nodo no determinado como la RX550 reportado como tal; o `drm-pdev` distinto para dos FDs del
  mismo dispositivo.
- `CURRENT_STATE`: `0000:01:00.0`, driver `amdgpu`, para `card1` y `renderD129` (`HOST-C`). `OBSERVED`.
- `PROVENANCE`: `HUMAN_REQUIREMENT` (literal, `AGENTS.md:32`,`:177`) + `PRIMARY_KERNEL_SOURCE`.

### `RT-3` · `DRM_FILE_CLIENT_IDENTITY`

- `ENTITY / PROPERTY`: `DRM_FILE_CLIENT_IDENTITY` — identidad de un fichero abierto DRM.
- `DEFINITION`: un descriptor abierto resuelve a un `struct drm_file`, y ese `drm_file` se
  identifica por su `drm-client-id`. La identidad es **1:1 con `drm_file`**, no con el FD.
- `UNIT`: **`drm_file`**.
- `SOURCE`: `drm_file.c:142` `file->client_id = atomic64_inc_return(&ident);` ·
  `drm-usage-stats.rst:64-72`; cadena FD → `struct file` → `drm_file` vía `f->private_data`.
- `RELATION`: FD **N:1** → `drm_file`; `drm_file` **1:1** → `client_id`.
- `CARDINALITY`: varios FDs (dup/fork) pueden compartir un `drm_file`; **FD count ≠ client count**.
- `LIFETIME`: la del `drm_file`. En la implementación inspeccionada se asigna una vez y el contador
  no se reutiliza; la spec no promete ese comportamiento. Ver `MUTABILITY`.
- `MUTABILITY`: dos planos, que no se colapsan.
  - `IMPLEMENTATION_OBSERVED`: el core inspeccionado asigna `client_id` una vez, en
    `drm_file_alloc` (`drm_file.c:142`); **no se observó otra escritura** del campo en el código
    inspeccionado, y el contador es monotónico y no se reutiliza.
  - `INTERFACE_GUARANTEE`: la spec garantiza **unicidad** e **identificación** del cliente —
    *"Unique value"*, *"Conceptually the value should map 1:1 to the in kernel representation of
    `struct drm_file`"*, y sirve para distinguir FDs duplicados/compartidos. **No** garantiza
    estabilidad: el campo es **público** (`drm_file.h:281-282`, `u64 client_id;`, sin `const`) y la
    spec **no** lo declara inmutable. La inmutabilidad **no** se afirma como propiedad normativa.
  - No es la misma clase de atributo que `drm_file.pid`, que el core **sí** reasigna en una
    condición documentada (`RT-4`).
- `OBSERVABILITY`: `EXPOSED` por el core. El analizador llega a **`PRESENCE`**; **no** a `VALUE`
  (`fdinfo_attribution` es "presence only, never a value"), por tanto **no** a `DISCRIMINATION`.
- `WHAT_IT_PROVES` (por separado): `PRESENCE` → que el core emitió la clave.
  `VALUE` → el número. `DISCRIMINATION` → que dos FDs son **distintos** `drm_file`.
- `WHAT_IT_DOES_NOT_PROVE`: que el PID sea el cliente; que el `client_id` sea un PASID; que sea el
  *client-id* de page fault; que el número de FDs sea el número de clientes; **que la unicidad sea
  global** — la spec permite unicidad **por dispositivo**, y entonces `drm-pdev` debe estar presente
  y la identidad correcta es el **par `(drm-pdev, drm-client-id)`**.
- `FALSIFIER`: dos `drm_file` con el mismo `client_id`; o una implementación con `client_id`
  repetido entre dispositivos y `drm-pdev` presente (spec-conformante, resolvería `C-4`).
- `CURRENT_STATE`: 12 FDs con la clave **presente** (`12/12`), 4 procesos distintivos
  (1 `systemd`, 993 `systemd-logind`, 1825 `kwin_wayland`, 1923 `Xwayland`). Valor preservado al
  menos en pasada A: `client-id 71` (Xwayland). **Recuento de `client-id` distintos:
  `NOT_ESTABLISHED`** en el registro preservado — solo hay presencia, no valores.
- `PROVENANCE`: `AGENT_FORMALIZATION` (el texto no nombra `drm-client-id`) + `PRIMARY_KERNEL_SOURCE`.

### `RT-4` · `DRM_CLIENT_PROCESS_ASSOCIATION`

- `ENTITY / PROPERTY`: `DRM_CLIENT_PROCESS_ASSOCIATION` — el proceso que el núcleo asocia al `drm_file`. Es la **semántica del campo**, no la observación.
- `DEFINITION`: el kernel mantiene en cada `drm_file` el proceso que lo está usando. **No** es propietario estable ni identidad del cliente.
- `UNIT`: **`drm_file`**.
- `SOURCE`: `drm_file.c:143` `rcu_assign_pointer(file->pid, get_pid(task_tgid(current)));` — **TGID**, no PID de hilo.
- `RELATION`: `drm_file` **1:1 (actual)** → `struct pid`. N `drm_file` → 1 proceso.
- `CARDINALITY`: muchos `drm_file` pueden pertenecer al mismo proceso.
- `LIFETIME`: por instancia; cambia cuando cambia el usuario del fichero.
- `MUTABILITY`: **MUTABLE** por `drm_file_update_pid` (`rcu_replace_pointer`). **Condiciones**: (a) reasigna al `task_tgid(current)`; (b) **no** reasigna si `filp->was_master` (`if (filp->was_master) return;`); (c) no reasigna si el TGID es idéntico. **Razón documentada** (`drm_auth.c:215-242`): preservar `drm_master_check_perm` para el paso de FD estilo logind.
- `OBSERVABILITY`: **`NOT_EXPOSED`**. `drm_file.pid` no se publica en fdinfo ni por otra interfaz de usuario. Lo que sí se observa es la ruta `/proc/<pid>/fd/<n>`, que es **otra relación** y de **unidad FD**: `RT-9`. **No se sustituyen entre sí.**
- `WHAT_IT_PROVES`: nada por sí solo desde las superficies disponibles. Su valor es fijar la semántica contra la que `RT-9` debe compararse.
- `WHAT_IT_DOES_NOT_PROVE`: **que ese proceso sea el cliente**; ni que lo sea para siempre; ni nada sobre memoria o engine de ese proceso — esas estadísticas son del `drm_file`, no del PID. Para un master, el pid es el del **apertura original**, no del usuario actual.
- `FALSIFIER`: `drm_file_update_pid` inoperante; o un master cuyo pid siga al usuario actual.
- `CURRENT_STATE`: **no observable por esta vía.** El dato observado es el de `RT-9`.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE` (campo) · el texto humano **no** nombra proceso.

### `RT-9` · `DRM_FD_PROCESS_ASSOCIATION`

- `ENTITY / PROPERTY`: `DRM_FD_PROCESS_ASSOCIATION` — qué proceso **posee** cada FD DRM ahora.
- `DEFINITION`: para cada FD DRM enumerado, el proceso cuya tabla de descriptores lo contiene es conocido. Es **posesión del descriptor**, no identidad del `drm_file`.
- `UNIT`: **FD** (descriptor).
- `SOURCE`: `/proc/<pid>/fd/<n>` (symlink) y `/proc/<pid>/fdinfo/<n>` (contenido). Sin campo del núcleo implicado.
- `RELATION`: proceso → FD (**posesión**, 1:N) · FD → nodo (por el symlink).
- `CARDINALITY`: 1 proceso → N FDs; N FDs → 1 proceso. **Un proceso puede sostener varios FDs del mismo `drm_file`**: por eso esta relación **no** cuenta clientes.
- `LIFETIME`: la del FD; cambia en cada enumeración.
- `MUTABILITY`: re-evaluable; un FD puede desaparecer entre la enumeración y la lectura.
- `OBSERVABILITY`: `EXPOSED` y `READABLE`. Límite: "no existe" e "ilegible" **no** se distinguen desde el symlink.
- `WHAT_IT_PROVES`: qué proceso **tenía** ese descriptor en el instante de la lectura, y sobre qué nodo apunta.
- `WHAT_IT_DOES_NOT_PROVE`: **no** prueba que ese proceso sea el cliente; **no** distingue dos FDs del mismo `drm_file` de dos `drm_file` distintos; **no** prueba que el `drm_file.pid` del núcleo tenga ese valor (`RT-4`), porque la ruta refleja el **tenedor actual**, no el campo.
- `FALSIFIER`: una ruta `/proc/<pid>/fd/<n>` resuelta a un nodo DRM con un proceso distinto del propietario real del descriptor.
- `CURRENT_STATE`: 12 FDs DRM leídos bajo 4 procesos (1 `systemd`, 993 `systemd-logind`, 1825 `kwin_wayland` con 9, 1923 `Xwayland` FD 13). `OBSERVED` / `TEMPORALITY = 2025-09-25` / pre-C1.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE` (`/proc`) · el texto humano **no** nombra proceso.

### `RT-10` · `DRM_CLIENT_PCI_ASSOCIATION`

- `ENTITY / PROPERTY`: `DRM_CLIENT_PCI_ASSOCIATION` — a qué dispositivo PCI pertenece el `drm_file` de un cliente.
- `DEFINITION`: el `drm_file` resuelve, por su `minor`, a un `drm_device` y de ahí a un dispositivo PCI. La **fuente observable** de esa unión es `drm-pdev`, que es **atributo del dispositivo**.
- `UNIT`: `drm_file` (la relación); el valor observado es un **BDF**.
- `SOURCE`: cadena establecida `drm_file` → `minor` (R-05) → `drm_device` (R-06) → PCI (R-07); valor publicado por `drm-pdev` en `drm_show_fdinfo`, **ssi** `dev_is_pci`.
- `RELATION`: `drm_file` **N:1** → `drm_device`; `drm_device` **1:0:1** → `pci_dev`.
- `CARDINALITY`: N `drm_file` → 1 dispositivo. El valor `drm-pdev` es **constante** para todos los `drm_file` de un dispositivo.
- `LIFETIME`: la del `drm_device`.
- `MUTABILITY`: inmutable en la interfaz; la cadena es estructural.
- `OBSERVABILITY`: `drm-pdev` es `Optional` en la spec y condicional a que el dispositivo sea PCI. **Transporta solo el BDF**: no `vendor`, ni `device`, ni `class`.
- `WHAT_IT_PROVES`: que el fdinfo de ese cliente nombra el slot del dispositivo PCI. Combinado con sysfs, permite confirmar el dispositivo completo.
- `WHAT_IT_DOES_NOT_PROVE`: **no** identifica clientes — es el mismo valor para todos ellos; **no** sustituye a `drm-client-id` (`RT-3`); **no** identifica el proceso; **no** aporta `vendor`/`device`/`class`, que sysfs sí aporta y `drm-pdev` no.
- `FALSIFIER`: dos `drm_file` del mismo dispositivo con `drm-pdev` distinto; o un cliente cuyo `drm-pdev` nombre un dispositivo distinto del que sysfs prueba para su nodo.
- `CURRENT_STATE`: `drm-pdev` `0000:01:00.0` presente en los 12 FDs de `card1` y `renderD129`. `OBSERVED` / `TEMPORALITY = 2025-09-25` / pre-C1.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE` (cadena y clave) · `EXTERNAL_SPEC` (opcionalidad).


### `RT-5` · `DRM_MEMORY_ACCOUNTING`

- `ENTITY / PROPERTY`: `DRM_MEMORY_ACCOUNTING` — consumo de memoria **de un `drm_file`**.
- `DEFINITION`: bytes por región consumidos por los buffer objects de ese `drm_file`. Claves
  **separadas**: `drm-total-<region>` (= `private + shared`), `drm-shared-<region>`,
  `drm-active-<region>`, `drm-resident-<region>` (solo si `DRM_GEM_OBJECT_RESIDENT`),
  `drm-purgeable-<region>` (solo si `DRM_GEM_OBJECT_PURGEABLE`). `drm-memory-<region>` **existe en
  la spec y NO la emite el helper del core**.
- `UNIT`: **agregado por `drm_file`**.
- `SOURCE`: `drm_print_memory_stats` (`drm_file.c`) — recibe un `drm_memory_stats` **pre-agregado**;
  la iteración de `file->object_idr` ocurre en el **llamante** (`drm_gem.c:884`) ·
  `drm-usage-stats.rst:143-172`.
- `RELATION`: `drm_file` → agregado de memoria. `drm-shared` es el indicador de **buffer compartido
  entre ficheros** (*"more than a single handle"*), por lo que conecta con `RT-3`.
- `CARDINALITY`: 1 `drm_file` → 0:1 agregado.
- `LIFETIME`: derivada; cambia con `object_idr`.
- `MUTABILITY`: sí, con cada alta/baja de handle.
- `OBSERVABILITY`: **`EXPOSED` por el driver** vía `dev->driver->show_fdinfo`; **no por el core**.
- `WHAT_IT_PROVES`: el consumo agregado de **ese** `drm_file` en el instante leído.
- `WHAT_IT_DOES_NOT_PROVE`: **no** es inventario de objetos individuales; **no** es propiedad de un
  PID; `=0` **no** prueba no-uso. Que la unidad sea el `drm_file` lo afirma la **spec**, y el core
  **no lo garantiza** — depende del driver.
- `FALSIFIER`: una clave de memoria definida **por proceso** en la spec; o un agregado por proceso
  emitido con prefijo `drm-`.
- `CURRENT_STATE`: pasada A, por cliente: `VRAM 0 KiB`, `GTT 2184 KiB` (Xwayland). La pasada
  ampliada **no recolectó** estadísticas de memoria. `PARTIAL`.
- `PROVENANCE`: `EXTERNAL_SPEC` (unidad) + `PRIMARY_KERNEL_SOURCE` (claves emitidas) +
  `AGENT_FORMALIZATION` (recolección parcial).

### `RT-6` · `DRM_ENGINE_ACCOUNTING`

- `ENTITY / PROPERTY`: `DRM_ENGINE_ACCOUNTING` — tiempo de engine dedicado a trabajos de un `drm_file`.
- `DEFINITION`: `drm-engine-<key>` = ns que el engine pasó **ocupado ejecutando workloads
  pertenecientes a ese cliente**. Familia: `drm-engine-`, `drm-engine-capacity-`, `drm-cycles-`,
  `drm-total-cycles-`, `drm-maxfreq-`. `<key>` estable y único por engine.
- `UNIT`: `drm_file` × engine.
- `SOURCE`: `drm-usage-stats.rst:79-133` (**spec**; el core no mantiene estos contadores).
- `RELATION`: `drm_file` → contador por engine. `drm-maxfreq` → capacidad del engine (**no** del
  cliente).
- `CARDINALITY`: 1 `drm_file` → 0:N contadores.
- `LIFETIME`: contador del driver; acumulado desde su propio cero, no desde la apertura.
- `MUTABILITY`: **no monótona por diseño** — *"not required to be constantly monotonic"*; ante un
  valor menor, *"userspace is expected to stay with that larger previous value"*.
- `OBSERVABILITY`: **`EXPOSED` por el driver**; el analizador **no lo recolecta**.
- `WHAT_IT_PROVES`: `>0` ⇒ **trabajo ejecutado perteneciente a ese `drm_file`**.
- `WHAT_IT_DOES_NOT_PROVE`: `>0` **no** significa que un proceso esté ejecutándose ahora; **no**
  significa uso exclusivo del dispositivo; **no** es identidad de proceso; `=0` **no** significa
  "el proceso nunca usó la GPU" — puede ser un retroceso no recuperado, y requiere retener el máximo
  anterior.
- `FALSIFIER`: una clave `drm-engine-*` definida por proceso en la spec; o la spec declarándola
  monótona; o `0` documentado como "sin trabajo".
- `CURRENT_STATE`: **`NOT_OBSERVED`**. Cero ocurrencias de `drm-engine-` / `drm-cycles-` en todo el
  registro del proyecto.
- `PROVENANCE`: `EXTERNAL_SPEC` exclusivamente.

### `RT-7` · `AMDGPU_PASID_PROCESS_RELATION`

- `ENTITY / PROPERTY`: `AMDGPU_PASID_PROCESS_RELATION` — relación entre un espacio de direcciones GPU y un proceso.
- `DEFINITION`: un `PASID` **es un vmid**; su propósito declarado es *"used to link a vmid to a
  system process id"*.
- `UNIT`: **vmid**.
- `SOURCE`: documentación de amdgpu (`EXTERNAL_SPEC`). Implementación: **`SOURCE_INCOMPLETE`**
  (`drivers/gpu/drm/amdgpu/` 404 en 3 mecanismos).
- `RELATION`: `drm_file` → `driver_priv` **`ESTABLISHED`** (el campo existe) · `driver_priv` →
  `amdgpu_fpriv` → `VM` → `PASID` **`SOURCE_INCOMPLETE`** (cadena rota en el tramo 2) ·
  `PASID` → proceso **`ESTABLISHED` solo como afirmación documental y condicional**.
- `CARDINALITY`: `PASID` → proceso **1:0:1**, condicional.
- `LIFETIME`: `UNKNOWN` a nivel de fuente.
- `MUTABILITY`: `UNKNOWN`.
- `OBSERVABILITY`: **condicional y episódica** — *"If the process is active when the fault happens,
  the process information will be printed"*.
- `WHAT_IT_PROVES`: fuera de un page fault, **nada**.
- `WHAT_IT_DOES_NOT_PROVE`: que `PASID` sea un `drm-client-id` (**son entidades distintas**); que
  sea un PID; que sirva como identidad de cliente; que la co-ocurrencia de un `pasid` y un PID en
  una tabla de auditoría **constituya** la relación — eso es un `join` de
  `AGENT_FORMALIZATION`, no un enlace del kernel.
- `FALSIFIER`: un `PASID` impreso con un PID sin page fault concurrente.
- `CURRENT_STATE`: `pasid 43` observado en pasada A para el único cliente legible de `card1`. La
  relación `PASID` → PID en el sentido técnico: **`NOT_ESTABLISHED`**. `SOURCE_INCOMPLETE` para el
  puente con `drm_file`.
- `PROVENANCE`: `EXTERNAL_SPEC` + `SOURCE_INCOMPLETE`.

### `RT-8` · `GPU_PAGE_FAULT_CLIENT_ID`

- `ENTITY / PROPERTY`: `GPU_PAGE_FAULT_CLIENT_ID` — identidad de la unidad de hardware que causó un
  fault.
- `DEFINITION`: **entidad distinta de `RT-3`**. Identifica un **bloque del motor**, no un fichero
  abierto. La palabra "client" aquí designa hardware.
- `UNIT`: bloque del motor (p. ej. `CPF`, `CPC`, `SDMA`, `VCN`, `JPEG`).
- `SOURCE`: **`SOURCE_INCOMPLETE`** — implementación en `drivers/gpu/drm/amdgpu/`, inaccesible.
- `RELATION`: **`NOT_ESTABLISHED`** con `drm_file` o con `client_id`.
- `CARDINALITY`: `UNKNOWN`.
- `LIFETIME` / `MUTABILITY` / `OBSERVABILITY`: `UNKNOWN` / `NOT_EXPOSED` por vía accesible.
- `WHAT_IT_PROVES`: **`NOT_ESTABLISHED`**.
- `WHAT_IT_DOES_NOT_PROVE`: que sea un `drm-client-id`. Colisión terminológica registrada como
  `C-1`, **`CONFLICT_UNRESOLVED`**.
- `FALSIFIER`: una fuente primaria que muestre que el page-fault `client-id` **es**
  `file->client_id`.
- `CURRENT_STATE`: `NOT_OBSERVED` y `SOURCE_INCOMPLETE`.
- `PROVENANCE`: `SOURCE_INCOMPLETE`.

### 2.1 Lo que deliberadamente NO es una propiedad

- **FD → proceso → cliente** (cadena de `RT-9` + `RT-3`): es una **composición**, no una propiedad
  nueva. Crear `CLIENT_PROCESS_ASSOCIATION` reintroduciría el contenedor que se está reparando.
- **`NODE_COMPLETENESS` ∧ `DRM_FILE_CLIENT_IDENTITY`**: dos propiedades con dos veredictos
  independientes. Fusionarlas recrea la fila compuesta original.
- **Cualquier tupla de campos** con `any()`/`all()`: unifica fuentes y dominios. No se crea.

---

## 3 · `PROVENANCE` — resumen

| Propiedad | `HUMAN_REQUIREMENT` | `PRIMARY_KERNEL_SOURCE` | `AGENT_FORMALIZATION` | `INFERENCE` |
|---|---|---|---|---|
| `RT-1 NODE_COMPLETENESS` | **sí** (*"complete"*, *"FD visibility is incomplete"*) | sí | sí (filas previas) | no |
| `RT-2 DRM_NODE_PCI_IDENTITY` | **sí** (literal) | sí | no | no |
| `RT-3 DRM_FILE_CLIENT_IDENTITY` | **no** | sí | **sí** | no |
| `RT-4 DRM_CLIENT_PROCESS_ASSOCIATION` | **no** (como requisito) | sí (campo) | no | no |
| `RT-9 DRM_FD_PROCESS_ASSOCIATION` | **no** (como requisito) | no (vía `/proc`) | sí (recorrido) | **sí** |
| `RT-5 DRM_MEMORY_ACCOUNTING` | **no** | parcial (claves) | sí (recolección) | no |
| `RT-6 DRM_ENGINE_ACCOUNTING` | **no** | no (solo spec) | no | no |
| `RT-7 AMDGPU_PASID_PROCESS_RELATION` | **no** | `SOURCE_INCOMPLETE` | no | no |
| `RT-10 DRM_CLIENT_PCI_ASSOCIATION` | **no** | sí (cadena) | sí (por `drm-pdev`) | no |
| `RT-8 GPU_PAGE_FAULT_CLIENT_ID` | **no** | `SOURCE_INCOMPLETE` | no | no |

**Ninguna propiedad creada por el agente adquiere autoridad normativa por existir.** `RT-3` a `RT-8`
son técnicamente definibles y Normativamente **no exigidas**: eso es `PROJECT_MAPPING`, y está diferido.

---

## 4 · Revisión de conclusiones que dependían de "attributable"

### `VALIDAS` — no dependían del término
- El modelo técnico v3 completo (17 entidades, 16 relaciones, `C-1`…`C-4`, 18 falsificadores).
- `FD count ≠ distinct client-id count` cuando varios FDs comparten un `drm_file` (**R-03**).
- `drm-pdev` no discrimina clientes; es constante por dispositivo (**E-5**).
- `drm_file.pid` es mutable con excepción `was_master`, y su razón está documentada (**E-9**).
- `PASID` ≠ `drm-client-id`; page-fault `client-id` ≠ `drm-client-id` (**C-1**, `C-2`).
- `drm-engine-*` es acumulado, no monotónico, y `=0` no prueba no-uso (**E-13**).
- `engine = 0` / `>0` no es identidad de proceso.
- `P5 = SOURCE_INCOMPLETE`; `drm-master` es transferible (**E-10**).

### `INVALIDADAS`
- **"`attributable` es una propiedad técnica"** — `REFUTED`: era un contenedor de ocho.
- **`DRM_ATTRIBUTION_FIELDS` como criterio de fila** — `REFUTED`: agrupa `client_id` (grupo 1),
  `pdev` (grupo 2) y `pasid` (grupo 7), que son relaciones distintas.
- **La fila de nodo como descripción de una propiedad** — `REFUTED`: la expresión computaba
  completitud **y** un predicado de atribución no definido. `:1557-1558` decía *"complete and
  attributable"*; `df2406a:2750-2751` computaba solo completitud.
- **`any()` sobre 3 campos heterogéneos** — `REFUTED`: es un híbrido `∀fd : ∃field` sobre tres
  relaciones ajenas, con unidades distintas.
- **"1 DRM client"** (pasada A) — ya `REFUTED` por cobertura ampliada a 12 FDs.
- **"12 clientes"** (pasada ampliada) — `REFUTED` como enunciado: son **12 FDs en 4 procesos**, y
  el recuento de `client-id` **distintos** es `NOT_ESTABLISHED`.

### `REQUIEREN_REFORMULACIÓN`
- **`card_clients` / `render_clients`** → reescribir como dos cosas: el **recuento de FDs que
  satisfacen un predicado** (`IMPLEMENTATION_FACT`) y, si se quiere, el **recuento de
  `drm_file` distintos** (`RT-3`/`DISCRIMINATION`). Nombre actual: `NAME_NOT_EVIDENCE`.
- **`drm_fds_enumerated`** → separar `RT-1` (enumeración, por nodo) de la atribución. El
  agrupamiento **pooled** card+render no corresponde a ninguna de las ocho propiedades.
- **`card_node_complete` / `render_node_complete`** →WITHDRAWN como nombre de propiedad.
  Descomposición en `RT-1` + `RT-3` con verdictos separados.
- **`clients_pasid_attributable`** → `NAME_NOT_EVIDENCE`: nominaba `RT-3` + `RT-7` + `RT-8`, que
  pertenecen a dominios distintos y tienen fuentes distintas.
- **`G-1` / `G-2`** → `REQUIEREN_REFORMULACIÓN`: se
 cierra porque el objeto de "attributable" ya
  **no es recuperable** y su resolución ya no bloquea: la reparación de §2 es independiente de él.

### `NO AFECTADAS`
- Las 6 correcciones de collector y sus tests (`AGENTS_V3_RACE_STRICTER_THAN_COLLECTOR`,
  `*_namespace_disappeared`, `namespace_errors`, Opción A, etc.): su justificación es
  `/proc`-cobertura y corrección de carrera, **no** atribución.
- Toda la investigación de P0–P12, poder, clocks, VRAM, I/O.
- `AGENTS.md` `:176-177` **permanece sin editar** — el texto humano no se reescribe; la reparación
  es un documento aparte.

---

## 5 · `PROJECT_MAPPING = DEFERRED_PENDING_SPEC_CLOSURE`

Lo que **no** se decide aquí, por instrucción y por coherencia:

- qué significa "evidencia completa" **para el requisito**;
- qué propiedades debe exigir `OWNERSHIP=FULL`;
- qué campos son obligatorios;
- `any()`/`all()` sobre cualquier conjunto;
- `PASS`/`FAIL` de cualquiera de las ocho;
- qué debe cambiar el collector.

**Cierre de la especificación**: alcanzado — 8/8 propiedades con nombre inequívoco, entidad, fuente,
relación, unidad, cardinalidad, lifetime, mutabilidad, observabilidad, qué prueba, qué no, falsificador,
estado actual y procedencia. `SPEC_STATUS = CLOSED_WITH_THREE_DECLARED_LIMITS`:
`RT-7` y `RT-8` `SOURCE_INCOMPLETE`; `RT-6` `NOT_OBSERVED`; `RT-3` `DISCRIMINATION` `NOT_ESTABLISHED`.

`PROJECT_MAPPING` es la fase siguiente y **requiere autorización propia**.

---

## 6 · Qué se reparó y por qué

| Parte del requisito original | Veredicto | Por qué |
|---|---|---|
| *"complete"* | **REPARADA** → `RT-1` | semántica recuperable; fuente `/proc`, sin fdinfo |
| *"card and render nodes"* | **REPARADA** → `RT-1` + `RT-2` por nodo | el ámbito es explícito; las propiedades se separan |
| *"identified by PCI identity rather than by node name"* | **CONSERVADA** → `RT-2` | literal, sin ambigüedad |
| *"FD visibility is incomplete"* (cláusula de fallo) | **CONSERVADA** | coherente con `RT-1` |
| *"a client is active"* | **NO CONVERTIDA** | no se sabe qué califica; se conserva como texto humano |
| *"attributable"* | **REPARADA** por separación en `RT-3`, `RT-4`, `RT-5`, `RT-6`, `RT-7`, `RT-8` | seis propiedades con unidades y fuentes distintas; el objeto original **no es recuperable** y no se reintenta |
| lista de `54b3ea8` (namespaces, writers, agents, PM, Btrfs, guard…) | **FUERA DE ALCANCE** | no pertenecen al dominio DRM; se mantienen sin cambios |

## 7 · Lo que esta ronda no hizo

No implementó código · no modificó collector, tests, `AGENTS.md`, `README` ni documentación previa ·
no commiteó · no ejecutó sudo, systemctl, C1, `--run`, runtime, benchmarks, tuning, ni cambios en
sysfs/GPU/PM/storage · no re-derivó ninguna fuente del modelo v3 · no buscó ninguna intención humana · no decidió
`PROJECT_MAPPING`.

---

# 8 · CIERRE DEL MODELO TÉCNICO

`TECHNICAL_MODEL_STATUS = CLOSED`. No queda ninguna propiedad técnica llamada `attributable`, ni
ninguna que agrupe dominios distintos. `PROJECT_MAPPING = NOT_ATTEMPTED`.

## 8.1 Propiedades cerradas

| # | `NAME` | `ENTITY/UNIT` | `SOURCE` | `PREDICATE` | `OBSERVABILITY` | `LIMITATIONS` | `FALSIFIER` | `PROVENANCE` |
|---|---|---|---|---|---|---|---|---|
| 1 | `DRM_FD_ENUMERATION` | FD | symlink `/proc/*/fd` | el symlink resolvió a un nodo DRM | `EXPOSED`+`READABLE` | "no existe" ≡ "ilegible" | un symlock resuelto a otro nodo | `PRIMARY_KERNEL_SOURCE` |
| 2 | `DRM_FDINFO_READABILITY` | FD | `/proc/*/fdinfo/*` | el texto leído no está vacío | `EXPOSED`+`READABLE` | no distingue lectura vacía de lectura sin claves | un fdinfo legible con texto no vacío y aún así contado ilegible | `PRIMARY_KERNEL_SOURCE` |
| 3 | `DRM_NODE_COMPLETENESS` | descriptor / proceso | `/proc/*/fd` + los 4 términos de visibilidad | 0 denegados, 0 otros errores, 0 permisos de la corrida, 0 previos sin resolver | `EXPOSED`+`READABLE` | **no hay contador de descriptor-no-resuelto por nodo**: la parte de nodo es `NOT_INDEPENDENTLY_MEASURED` | un descriptor sin resolver que no degradara la propiedad | `PRIMARY_KERNEL_SOURCE` + `HUMAN_REQUIREMENT` (*"complete"*) |
| 4 | `DRM_PCI_DEVICE_IDENTITY` | nodo (`drm_minor`) | sysfs; `minor->dev`; `dev_is_pci` | BDF+vendor+device+class+driver coinciden | `EXPOSED`+`READABLE` sin leer fdinfo | `cardN` no es identidad entre hosts | un nodo no determinado como la RX550 | `PRIMARY_KERNEL_SOURCE` + `HUMAN_REQUIREMENT` (literal) |
| 5 | `DRM_CLIENT_ID_PRESENCE` | **FD** (no `drm_file`) | clave `drm-client-id:` en fdinfo | la clave está presente | `EXPOSED`; el analizador llega a `PRESENCE`, **no** a `VALUE` | **no** prueba identidad, ni discriminación, ni nº de clientes | dos `drm_file` con la misma clave | `PRIMARY_KERNEL_SOURCE` (`drm_file.c:142`, `drm_show_fdinfo`) |
| 6 | `DRM_PCI_ADDRESS_PRESENCE` | **FD** | clave `drm-pdev:` | la clave está presente | `EXPOSED`; condicional a que el dispositivo sea PCI | **constante por dispositivo**: no discrimina clientes; **no** transporta vendor/device/class | dos `drm_file` del mismo dispositivo con `drm-pdev` distinto | `PRIMARY_KERNEL_SOURCE` |
| 7 | `DRM_PASID_PRESENCE` | **FD** | clave `pasid:` | la clave está presente | `EXPOSED` pero **episódica** por definición | la relación `PASID`↔VM↔PID es **condicional** (page fault + proceso activo); el puente con `drm_file` es `SOURCE_INCOMPLETE` | un `PASID` impreso con PID sin page fault concurrente | `EXTERNAL_SPEC` (documentación amdgpu) |
| 8 | `PROCESS_ASSOCIATION` | `drm_file` (`RT-4`) y **FD** (`RT-9`) | `drm_file.pid` (no expuesta) · `/proc/<pid>/fd/<n>` | el campo del núcleo **no se observa**; la ruta sí | `RT-4` `NOT_EXPOSED` · `RT-9` `EXPOSED` | la ruta refleja el **tenedor actual**, no el campo | `drm_file_update_pid` inoperante | `PRIMARY_KERNEL_SOURCE` |

`LIFETIME`/`MUTABILITY`: `drm-client-id` se asigna una vez y el core no lo reasigna
(`IMPLEMENTATION_OBSERVED`); la **interfaz no promete estabilidad** y el campo es público
(`drm_file.h:281-282`). `drm_file.pid` es **mutable** con excepción `was_master`. `drm-pdev` y
`pasid` son **derivados al imprimir**, sin estado propio.

## 8.2 Lo que sigue técnicamente desconocido

| | `CLASS` |
|---|---|
| `drm-client-id` **distinto** — clave de deduplicación (`client_id` vs par `(drm-pdev, client-id)`) | `CONFLICT_UNRESOLVED` (`C-4`): la spec permite unicidad global **o** por dispositivo |
| relación `PASID` ↔ `amdgpu_vm` ↔ `drm_file` | `SOURCE_INCOMPLETE` — `drivers/gpu/drm/amdgpu/` inaccesible en 3 mecanismos |
| `GPU_PAGE_FAULT_CLIENT_ID` | `SOURCE_INCOMPLETE` |
| contenido de `driver_priv` para amdgpu | `SOURCE_INCOMPLETE` |
| `ENGINE_ACCOUNTING` / `MEMORY_ACCOUNTING` en este host | `NOT_OBSERVED`; la spec **sí** está disponible, luego no es `SOURCE_INCOMPLETE` |

**Ninguno de estos bloquea la descomposición**: son propiedades que no pueden definirse aún, y se
declaran como tales en vez de inventarse.

## 8.3 `REAL_DEFECT` — defecto de implementación, no propiedad

`any(fdinfo_attribution(client["fdinfo"]).values())` sobre
`DRM_ATTRIBUTION_FIELDS = ("drm-client-id", "drm-pdev", "pasid")` (collector `:1033`, `:2785`),
combinado como `node_attributable[n] == node_fd_count[n]` (`:2790-2791`).

`CLASS = REAL_DEFECT · IMPLEMENTATION`. Fusiona **tres dominios** (`RT-3`, `RT-6`, `RT-7`) en **un**
predicado y produce un `∀fd : ∃field` sobre campos que no son comparables. **No se corrige eligiendo
`any()` o `all()`**: la corrección es eliminar la propiedad compuesta y sustituirla por predicados
independientes, uno por propiedad.

`drm_pdev_seen` y `drm_pasid_seen` son **`ARCHITECTURE_DEFECT · producer→consumer`**: se
recolectan y se exportan, y **ningún consumidor los lee** desde el Paso 1. Eso es un defecto de
enrutado interno, **no** evidencia de que las propiedades carezcan de significado: ambas están
definidas arriba con unidad, fuente y falsificador.

## 8.4 Cambios de código que la descomposición requiere — **NO EJECUTADOS**

| Archivo | Símbolo | Propiedad afectada | Cambio | Test que lo falsifica |
|---|---|---|---|---|
| `privileged_read_collector.py` | `DRM_ATTRIBUTION_FIELDS` `:1033` | las 3 | eliminar la tupla; una constante por propiedad | ninguno hoy: **`GAP`** |
| `privileged_read_collector.py` | `any(fdinfo_attribution(...).values())` `:2785` | las 3 | un predicado por clave: `("drm-client-id:", …)`, `("drm-pdev:", …)`, `("pasid:", …)` | `test_each_node_row_has_its_own_completeness_term` no lo cubre: **`GAP`** |
| `privileged_read_collector.py` | `node_attributable` `:2777-2791` | `RT-3`,`RT-6`,`RT-7` | tres contadores por nodo, sin conjunción | **`GAP`** |
| `privileged_read_collector.py` | `drm_pdev_seen`, `drm_pasid_seen` `:2850-2851` | `RT-6`, `RT-7` | exportarlos con estado y razón propios, para que un consumidor los lea | **`GAP`** |
| `test_med_review_classifications.py` | — | las 3 | tres tests de comportamiento, uno por propiedad | — |

**Los `GAP` son el trabajo pendiente**: hoy no existe ningún test que detecte si el predicado
compuesto reaparece. Es el **siguiente paso mínimo y verificable**, y es anterior a cualquier
cambio de `ownership_matrix` o de las 12 fixtures.

**Verificado antes de proponer**: el reemplazo por tres predicados **no introduce otra propiedad
compuesta disfrazada** — cada uno lee **una** clave y devuelve **un** estado, sin `any()`/`all()`
entre dominios, y ninguno se conjuga con `card_complete`/`render_complete`.
