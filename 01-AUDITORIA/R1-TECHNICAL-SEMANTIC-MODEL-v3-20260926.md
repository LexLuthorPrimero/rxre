# R1-TECHNICAL-SEMANTIC-MODEL-20260926 · v3 FINAL

`TECHNICAL_MODEL_VERSION` = **3.0** · `TECHNICAL_MODEL_STATUS` = **`CLOSED`**
Consolida v1 (`R1-TECHNICAL-SEMANTIC-MODEL-20260926.md`, `HISTORICAL`) y v2
(`R1-TECHNICAL-SEMANTIC-MODEL-v2-20260926.md`, `HISTORICAL`). No reescribe ni elimina ninguno.
`PROJECT_MAPPING` = **`NOT_ATTEMPTED`**
`CODE_CHANGE_ALLOWED` = `NO` · `READ_ONLY` estricto · nada modificado, ejecutado ni commiteado.

Alcance: *"¿qué entidades, atributos y relaciones están definidas por las fuentes primarias de Linux
DRM y qué puede observarse de ellas?"*. **No** decide el significado de `complete attributable
evidence`, ni qué campos son obligatorios, ni `any`/`all`, ni PASS/FAIL, ni qué debe exigir
`OWNERSHIP=FULL`, ni qué debe cambiar el collector.

`TEMPORALITY` = `linux` v6.12 mainline, leído en esta sesión · `HOST_SCOPE` = ninguno.

---

## 0 · `SOURCE_COVERAGE` y `PROVENANCE`

Fuentes primarias, todas leídas: `drivers/gpu/drm/drm_file.c` (996 L) · `include/drm/drm_file.h` ·
`drivers/gpu/drm/drm_lease.c` (733 L) · `drivers/gpu/drm/drm_auth.c` (467 L) ·
`include/drm/drm_lease.h` · `include/drm/drm_auth.h` · `include/drm/drm_gem.h` (637 L) ·
`drivers/gpu/drm/drm_gem.c` (1535 L) · `include/drm/drm_drv.h` (554 L) ·
`drivers/gpu/drm/drm_internal.h` · `Documentation/gpu/drm-usage-stats.rst` (189 L).

`drivers/gpu/drm/amdgpu/**` → `SOURCE_INCOMPLETE` (404 en `raw.githubusercontent`, en la API de
contenidos de GitHub y en `kernel.org/doc`).

| `PROVENANCE` | Alcance |
|---|---|
| `PRIMARY_KERNEL_SOURCE` | toda la §2 y §3 salvo lo marcado `SOURCE_INCOMPLETE` |
| `EXTERNAL_SPEC` | `drm-usage-stats.rst`; docs de amdgpu |
| `PROJECT_DOCUMENT` | **no aparece** como semántica del kernel en ninguna línea |
| `AGENT_FORMALIZATION` | §8 únicamente, y siempre etiquetado |
| `INFERENCE` | marcado como tal; nunca presentado como hecho del kernel |

**Ninguna afirmación de §2–§7 procede de un documento del proyecto.** Una propiedad observada en
una implementación no se convierte en regla del modelo (ver `drm-client-id`, §4).

---

## 1 · REGLAS DE SEPARACIÓN (transversales)

**1.1 Cadena de observabilidad** — `EXPOSED_BY_SYSTEM` → `READABLE_BY_ANALYZER` →
`OBSERVED_IN_SAMPLE` → `PROVES_PROPERTY` → `SATISFIES_PROJECT_REQUIREMENT`.
Una capa ausente rompe la cadena; lo posterior es `NOT_ESTABLISHED`.

**1.2 Cadena de capacidad** — `PRESENCE` → `VALUE` → `DISCRIMINATION` → `ATTRIBUTION`.
Precondiciones estrictamente crecientes; ninguna se infiere de la anterior.

**1.3 Grupos de separación exigidos.** Ningún nombre genérico (`ATTRIBUTABLE`,
`DRM_ATTRIBUTION_FIELDS` o equivalente) es contenedor de más de uno:

| Grupo | Entidades | En § |
|---|---|---|
| 1 · identidad de fichero/cliente | `drm_file`, `drm-client-id` | E-3, E-4 |
| 2 · identidad de dispositivo | `drm_device`, `drm_minor`, `drm-pdev` | E-5, E-6, E-7, E-8 |
| 3 · asociación con proceso | `drm_file.pid` | E-9 |
| 4 · objetos y memoria | `object_idr`, GEM object, memory statistics | E-11, E-12 |
| 5 · ejecución | `drm-engine-*` y familia | E-13 |
| 6 · VM/PASID | `VM`, `PASID`, page-fault `client-id` | E-15, E-16, E-17 |
| 7 · master | `drm_master`, `file->master`, `is_master`, `was_master` | E-10 |
| 8 · FD | userspace FD, `struct file`, `drm_file` | E-1, E-2, E-3 |

---

## 2 · MODELO DE ENTIDADES

### E-1 · `FD` (userspace file descriptor)
- `DEFINITION`: entrada de la tabla de descriptores de un proceso.
- `UNIT`: un descriptor.
- `SOURCE`: VFS, fuera del árbol DRM leído.
- `LIFETIME`: `open()` → `close()`. `dup()`/`fork()` **no** crean un `struct file` nuevo.
- `IDENTITY_SEMANTICS`: **ninguna identidad DRM**. No es `drm-client-id`; puede compartirlo.
- `MUTABILITY`: puede cambiar de proceso por herencia; el `drm_file` que referencia, no.
- `OBSERVABILITY`: `EXPOSED` como `/proc/<pid>/fd/<n>`; `READABLE` como symlink.
- `KNOWN_LIMITS`: el path **no distingue** dos `drm_file` distintos → **no puede ser unidad de
  identidad**.
- `FALSIFIER`: dos FDs que un `struct file` distingue y un `drm_file` no.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE` (parcial), `INFERENCE` (VFS no leído).

### E-2 · `struct file` (`filp`)
- `DEFINITION`: objeto kernel de fichero abierto; contiene `private_data`.
- `UNIT`: un `struct file`.
- `SOURCE`: `drm_file.c` — `struct drm_file *file = f->private_data;`.
- `LIFETIME`: refcount por FD; liberado al último `fput`.
- `IDENTITY_SEMANTICS`: `private_data` ↔ `drm_file` es **1:1**.
- `MUTABILITY`: `private_data` no se reasigna.
- `OBSERVABILITY`: **`NOT_EXPOSED`**. Sin superficie directa.
- `KNOWN_LIMITS`: solo **inferible** por la 1:1 con `drm_file`.
- `FALSIFIER`: un `struct file` con dos `drm_file`, o un `drm_file` en dos `struct file`.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE`.

### E-3 · `struct drm_file`
- `DEFINITION`: estado DRM por fichero abierto; "userspace client" según `drm-internals`.
- `UNIT`: **una apertura DRM**.
- `SOURCE`: `drm_file.h`; asignación en `drm_file.c:142-144`.
- `LIFETIME`: `drm_file_alloc()` en la apertura; `drm_file_put` en el cierre; nodo en
  `dev->filelist` mientras existe.
- `IDENTITY_SEMANTICS`: no tiene identidad propia comparable. Lo identifican `client_id` (estable)
  y `magic` (autenticación legacy).
- `MUTABILITY`: `object_idr`, `master`, `is_master`, `pid`, `driver_priv` mutables;
  `client_id` y `minor` **asignados una vez** por el core, **sin reasignación observada** en el
  código inspeccionado. Ese alcance es de implementación, no un contrato de la interfaz: ambos
  campos son públicos. Ver `E-4` para el desglose de los dos planos.
- `OBSERVABILITY`: **`NOT_EXPOSED` directamente**; observable solo por las claves que lo resumen.
- `KNOWN_LIMITS`: su **existencia** no es observable si no se lee `drm-client-id`.
- `FALSIFIER`: un `drm_file` vivo y funcional sin ninguna clave de fdinfo que lo identifique, o dos
  `drm_file` con el mismo `client_id`.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE`.

### E-4 · `drm-client-id`
- `DEFINITION`: clave fdinfo `Optional` para *"distinguish duplicated and shared file descriptors"*.
- `UNIT`: un `drm_file`.
- `SOURCE`: `drm_file.c:142` `file->client_id = atomic64_inc_return(&ident);` ·
  spec `drm-usage-stats.rst:64-72`.
- `LIFETIME`: la del `drm_file`. En la implementación inspeccionada se asigna una vez y el contador
  no se reutiliza; la spec no promete ese comportamiento. Ver `MUTABILITY`.
- `IDENTITY_SEMANTICS`: **1:1 con `drm_file` por construcción en la implementación inspeccionada**.
  Unicidad según §4.
- `MUTABILITY`: dos planos, que no se colapsan.
  - `IMPLEMENTATION_OBSERVED`: una **única** escritura en todo el core leído —
    `drm_file.c:142` en `drm_file_alloc`; las otras coincidencias son la lectura (`:943`) y la
    declaración. Contador monotónico, no reutilizado.
  - `INTERFACE_GUARANTEE`: la spec garantiza **unicidad** e **identificación** — *"Unique value"*,
    mapeo conceptual 1:1 con `struct drm_file`, y distinción de FDs duplicados/compartidos;
    unicidad **global o por dispositivo**, en cuyo caso `drm-pdev` debe estar presente. **No**
    garantiza estabilidad: `drm_file.h:281-282` declara `u64 client_id;` **público y sin `const`**,
    y la spec **no** lo declara inmutable. **La inmutabilidad no se afirma como propiedad normativa.**
- `OBSERVABILITY`: `EXPOSED` **por el core**, incondicional dentro de `drm_show_fdinfo`.
- `KNOWN_LIMITS`: §4 completo. **No** es FD, **no** es PID, **no** es proceso, **no** es
  `drm_master`, **no** es el page-fault `client-id`.
- `FALSIFIER`: dos `drm_file` con el mismo `client_id`; o una implementación que lo asigne **por
  dispositivo** con `drm-pdev` presente (spec-conformante, resolvería `C-4`).
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE` (implementación) + `EXTERNAL_SPEC` (alcance de unicidad).

### E-5 · `drm-pdev`
- `DEFINITION`: clave fdinfo `Optional`: *"the PCI **slot address** of the device in question"*.
- `UNIT`: un dispositivo PCI. Valor `domain:bus:slot.func`.
- `SOURCE`: `drm_show_fdinfo` — `if (dev_is_pci(dev->dev))` con `dev = file->minor->dev`.
- `LIFETIME`: **no tiene**: no se almacena, se **deriva al imprimir**.
- `IDENTITY_SEMANTICS`: identifica **el dispositivo**, no el cliente. **Constante** para todos los
  `drm_file` de un mismo dispositivo → **no discrimina clientes**.
- `MUTABILITY`: no aplicable.
- `OBSERVABILITY`: `EXPOSED` **ssi** el dispositivo es PCI.
- `KNOWN_LIMITS`: **no** incluye `vendor`, `device` ni `class` → **no basta** para probar identidad
  de dispositivo por sí sola.
- `FALSIFIER`: dos `drm_file` del mismo dispositivo con `drm-pdev` distinto; o un dispositivo
  PCI-backed sin `drm-pdev`, o uno no-PCI con ella.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE`.

### E-6 · `struct drm_minor`
- `DEFINITION`: un nodo de dispositivo DRM (`/dev/dri/N`).
- `UNIT`: un nodo. Campos: `index` (nº de minor), `type`, `kdev`, `dev`.
- `SOURCE`: `drm_file.h:77-87`.
- `LIFETIME`: registrado con el `drm_device`; sobrevive a todos sus `drm_file`.
- `IDENTITY_SEMANTICS`: identidad = (`index`, `type`).
- `MUTABILITY`: inmutable tras el registro.
- `OBSERVABILITY`: `EXPOSED` vía sysfs.
- `KNOWN_LIMITS`: **`cardN` no es identidad de dispositivo**; depende del orden de registro y
  difiere entre hosts.
- `FALSIFIER`: dos `drm_device` para un `drm_minor`, o un `drm_file` accesible desde dos nodos.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE`.

### E-7 · `struct drm_device`
- `DEFINITION`: estado de un driver+dispositivo.
- `UNIT`: un driver+dispositivo. Contiene `struct device *dev` embebido.
- `SOURCE`: `drm_drv.h`; relación `minor->dev` (`drm_file.h:82`).
- `LIFETIME`: probe → remove; padre de sus minors.
- `IDENTITY_SEMANTICS`: la del `struct device` embebido.
- `MUTABILITY`: mayormente inmutable tras el probe; `filelist` es concurrente.
- `OBSERVABILITY`: `EXPOSED` vía sysfs.
- `KNOWN_LIMITS`: **no tiene identidad DRM serial**.
- `FALSIFIER`: dos `drm_device` con el mismo `struct device`.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE`.

### E-8 · PCI device
- `DEFINITION`: dispositivo PCIe con BDF, `vendor`, `device`, `class`.
- `UNIT`: un dispositivo.
- `SOURCE`: rama `dev_is_pci` + `to_pci_dev`; `drm-pdev` por `pci_domain_nr`, `pdev->bus->number`,
  `PCI_SLOT`, `PCI_FUNC`.
- `LIFETIME`: registrar/desregistrar.
- `IDENTITY_SEMANTICS`: **BDF** — la única identidad de dispositivo portable entre hosts.
- `MUTABILITY`: inmutable.
- `OBSERVABILITY`: `EXPOSED` vía sysfs; `EXPOSED` **parcialmente** vía `drm-pdev` (**solo BDF**).
- `KNOWN_LIMITS`: `drm-pdev` **no** transporta `vendor`/`device`/`class`.
- `FALSIFIER`: ver E-5.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE`.

### E-9 · `drm_file.pid` — PID/TGID
- `DEFINITION`: `struct pid *` que representa el proceso que usa el `drm_file`.
- `UNIT`: un `task_struct`, identificado por **TGID** (no PID de hilo).
- `SOURCE`: `drm_file.c:143` `rcu_assign_pointer(file->pid, get_pid(task_tgid(current)));`
- `LIFETIME`: referencia `struct pid` con `get_pid`/`put_pid`.
- `IDENTITY_SEMANTICS`: **el proceso que usa el archivo, no su propietario estable**. No es
  identidad de cliente.
- `MUTABILITY`: **MUTABLE** por `drm_file_update_pid` (`rcu_replace_pointer`).
  **Condiciones**: (a) se reasigna al `task_tgid(current)` del que llama; (b) **no** se reasigna
  si `filp->was_master` es verdadero — `if (filp->was_master) return;`; (c) no se reasigna si el
  `task_tgid` es idéntico al actual. **Razón documentada** (`drm_auth.c:215-242`): preservar
  `drm_master_check_perm`, que compara `was_master && pid == task_tgid(current)`, y que existe para
  que el paso de FD estilo logind siga funcionando sin `CAP_SYS_ADMIN`.
- `OBSERVABILITY`: **`drm_file.pid` NO se expone en fdinfo**. Observable **solo** por
  `/proc/<pid>/fd/<n>`, que es el **FD poseído ahora** — un proxy relacionado, no el campo.
- `KNOWN_LIMITS`: (a) para un master el pid es el del **apertor original**; (b) el path `/proc` no
  es el campo `pid` del `drm_file`.
- `FALSIFIER`: `drm_file_update_pid` inoperante; o un master cuyo pid siga al usuario actual; o
  `drm_file.pid` ausente para un `drm_file` vivo.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE`.

### E-10 · `drm_master`, `file->master`, `is_master`, `was_master`
- `DEFINITION`: propiedad de recursos de display, con identidad **separada** del `drm_file`:
  `unique`, `magic_map`, `lessee_id`, `lessor`, `lessees`, `leases`, `lessee_idr`.
- `UNIT`: un master.
- `SOURCE`: `drm_lease.h` (`struct drm_master`) · `drm_lease.c` · `drm_auth.c` ·
  `drm_file.h:218,229,266`.
- `LIFETIME`: `kref`. Se crea al obtener master. **Transferible**: `lessee->lessor =
  drm_master_get(lessor)` (`drm_lease.c:247`).
- `IDENTITY_SEMANTICS`: **no es el `drm_file`**. `is_master` = *"This client is the **creator** of
  @master"*; un lessee también puede ser `is_master` (`drm_lease.c:562`). `was_master` = *"has or
  had, master capability"*, **sticky** (solo se asigna `true`, `drm_auth.c:160`).
- `MUTABILITY`: `master` y `is_master` mutables; `was_master` **monótono**.
- `OBSERVABILITY`: por ioctl. **`NOT_EXPOSED` en fdinfo**.
- `KNOWN_LIMITS`: **la propiedad de un master puede pasar de un proceso a otro** por leasing →
  `drm_master` **no es identidad de proceso**. Solo existe en nodos con tipo primario.
- `FALSIFIER`: un master transferido sin `lessor`/`lessees`; o `was_master` puesto a `false`.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE`.
- **Separación explícita**: `drm_master ≠ drm-client-id`. El primero es una capacidad de display
  con transferencia; el segundo es un `u64` que identifica un fichero abierto. Un `drm_file`
  puede tenerlo o no.

### E-11 · GEM object / `object_idr`
- `DEFINITION`: objeto de buffer gestionado por GEM. Campos relevantes: `refcount` (`kref`),
  `handle_count`, `dev`, `list`.
- `UNIT`: un `drm_gem_object`.
- `SOURCE`: `include/drm/drm_gem.h`; `object_idr` en `drm_file.h`; iteración en `drm_gem.c:884`.
- `LIFETIME`: `refcount`; vive mientras alguien lo referencia.
- `IDENTITY_SEMANTICS`: **no tiene identidad propia observable**. Se referencia por **handle
  numérico dentro de un `object_idr`**, y ese idr **pertenece a un `drm_file`**.
- `MUTABILITY`: handles alta/baja; `handle_count` varía.
- `OBSERVABILITY`: **`NOT_EXPOSED` individualmente**. Solo el **agregado** se expone (§E-12).
- `KNOWN_LIMITS`: `handle_count` cuenta **handles**, y un handle es por `drm_file` → la spec
  define `drm-shared` como *"shared with another **file** (e.g., have more than a single handle)"*.
- `FALSIFIER`: un GEM object usado por un `drm_file` sin estar en su `object_idr`; o un handle
  contado en dos `object_idr` distintos.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE`.

### E-12 · memory statistics
- `DEFINITION`: desglose por región del consumo de buffer objects. **Claves separadas**, tal como
  las emite `print_size` (`drm-%s-%s` con `stat` ∈ {total, shared, active, resident, purgeable}):

  | Clave | Contenido | Condición |
  |---|---|---|
  | `drm-total-<region>` | `private + shared` | siempre |
  | `drm-shared-<region>` | `shared` | siempre |
  | `drm-active-<region>` | `active` | siempre |
  | `drm-resident-<region>` | `resident` | solo si `DRM_GEM_OBJECT_RESIDENT` |
  | `drm-purgeable-<region>` | `purgeable` | solo si `DRM_GEM_OBJECT_PURGEABLE` |
  | `drm-memory-<region>` | **en la spec, NO emitida por el helper del core** | — |

- `UNIT`: **agregado por `drm_file`**, no inventario de objetos.
- `SOURCE`: `drm_file.c` `drm_print_memory_stats` (recibe un `drm_memory_stats` **pre-agregado**) ·
  spec `drm-usage-stats.rst:143-172`.
- `LIFETIME`: **derivada**, sin almacenamiento propio en el core.
- `IDENTITY_SEMANTICS`: la unidad declarada por la spec es *"this client"* (= `drm_file`).
- `MUTABILITY`: cambia con `object_idr`.
- `OBSERVABILITY`: **`EXPOSED` por el driver**, vía `dev->driver->show_fdinfo`; **no por el core**.
- `KNOWN_LIMITS`: el core **no** produce ni valida estas estadísticas. Que la unidad sea el
  `drm_file` es una afirmación de la spec que el driver puede no cumplir. `=0` no prueba no-uso.
- `FALSIFIER`: una clave de memoria **por proceso** en la spec; o un agregado por proceso
  emitido con el prefijo `drm-`.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE` (claves emitidas) + `EXTERNAL_SPEC` (unidad declarada).

### E-13 · engine statistics
- `DEFINITION`: familia de contadores por engine: `drm-engine-<key>` (ns busy),
  `drm-engine-capacity-<key>`, `drm-cycles-<key>`, `drm-total-cycles-<key>`,
  `drm-maxfreq-<key>`. `drm-engine-<key>` = tiempo que el engine *"spent busy executing workloads
  **belonging to this client**"*.
- `UNIT`: `drm_file` × engine. `<key>` estable y único por engine.
- `SOURCE`: `drm-usage-stats.rst:79-133` (**spec**, no core).
- `LIFETIME`: contador **del driver**; el core no lo mantiene.
- `IDENTITY_SEMANTICS`: unidad declarada = **cliente** (`drm_file`).
- `MUTABILITY`: **no monótona por diseño** — *"not required to be constantly monotonic"*; ante un
  valor menor, *"userspace is expected to stay with that larger previous value"*.
- `OBSERVABILITY`: **`EXPOSED` por el driver**, no por el core.
- `KNOWN_LIMITS`: **no** se infiere: `engine == proceso`; `engine > 0 == proceso ejecutándose`;
  `engine == ownership exclusivo`; `engine == ENGINE_ACTIVITY del proyecto`. `>0` significa trabajo
  ejecutado *perteneciente a ese `drm_file`*, **tiempo acumulado**, no actividad actual. `=0`
  **no** prueba no-uso.
- `FALSIFIER`: una clave `drm-engine-*` definida por proceso en la spec; o la spec declarándola
  monótona; o `0` documentado como "sin trabajo".
- `PROVENANCE`: `EXTERNAL_SPEC` exclusivamente. **Sin fuente primaria del core** para su producción.

### E-14 · `driver_priv`
- `DEFINITION`: `void *` opaco, por `drm_file`, definido por el driver. También existe en
  `struct drm_master`.
- `UNIT`: un puntero.
- `SOURCE`: `drm_file.h`.
- `LIFETIME`: la del `drm_file`.
- `IDENTITY_SEMANTICS`: **ninguna** en el core.
- `MUTABILITY`: opaca.
- `OBSERVABILITY`: **`NOT_EXPOSED`**.
- `KNOWN_LIMITS`: **no usar su nombre como prueba de su contenido**. Para amdgpu:
  `SOURCE_INCOMPLETE`.
- `FALSIFIER`: `FALSIFICATION_STATUS = NOT_AVAILABLE` — el core no define su contenido, así que no
  hay afirmación que falsificar.
- `PROVENANCE`: `PRIMARY_KERNEL_SOURCE` (existencia) · contenido `SOURCE_INCOMPLETE`.

### E-15 · `VM` (espacio de direcciones GPU)
- `DEFINITION`: no establecida por fuente primaria accesible.
- `UNIT` / `LIFETIME` / `MUTABILITY` / `OBSERVABILITY`: `UNKNOWN`.
- `KNOWN_LIMITS`: **no puede afirmarse que exista una relación observable con `drm_file`**.
- `FALSIFIER`: `FALSIFICATION_STATUS = NOT_AVAILABLE` (`SOURCE_INCOMPLETE`).
- `PROVENANCE`: `SOURCE_INCOMPLETE`.

### E-16 · `PASID`
- `DEFINITION`: un **vmid**. Propósito declarado: *"used to link a vmid to a system process id"*.
- `UNIT`: un vmid.
- `SOURCE`: documentación de amdgpu (`EXTERNAL_SPEC`); implementación `SOURCE_INCOMPLETE`.
- `LIFETIME`: `UNKNOWN` a nivel de fuente.
- `IDENTITY_SEMANTICS`: identifica **un espacio de direcciones**, no un fichero, ni un cliente, ni
  un proceso.
- `MUTABILITY`: `UNKNOWN`.
- `OBSERVABILITY`: **condicional y episódica** — *"If the process is active when the fault happens,
  the process information will be printed"*.
- `KNOWN_LIMITS`: la relación con proceso existe **solo durante un page fault y solo si el proceso
  está activo en ese instante**. **No** es una relación estable ni consultable.
- `FALSIFIER`: un `PASID` impreso con un PID sin page fault concurrente.
- `PROVENANCE`: `EXTERNAL_SPEC`.

### E-17 · GPU page-fault `client-id`
- `DEFINITION`: **entidad distinta de E-4**. Identifica **la unidad de hardware (bloque del motor)
  que causó el fault**, no un fichero abierto.
- `UNIT`: un bloque del motor (p. ej. `CPF`, `CPC`, `SDMA`, `VCN`, `JPEG`).
- `SOURCE`: `SOURCE_INCOMPLETE` — la implementación está en `drivers/gpu/drm/amdgpu/`.
- `LIFETIME` / `MUTABILITY` / `OBSERVABILITY`: `UNKNOWN`.
- `KNOWN_LIMITS`: **el nombre colisiona con E-4 y no significa lo mismo** → `C-1`.
- `FALSIFIER`: una fuente primaria que muestre que el page-fault `client-id` **es**
  `file->client_id`.
- `PROVENANCE`: `SOURCE_INCOMPLETE`.

---

## 3 · MODELO DE RELACIONES

| ID | `RELATION` | `CARDINALITY` | `DIRECTION` | `SOURCE` | `TARGET` | `CONDITIONS` | `MUTABILITY` | `FALSIFIER` |
|---|---|---|---|---|---|---|---|---|
| R-01 | FD → `struct file` | N:1 | fd → file | VFS (no leído) | `struct file` | siempre | refcount | dos FDs con `struct file` distinto para el mismo fichero abierto |
| R-02 | `struct file` → `drm_file` | **1:1** | file → `private_data` | `drm_file.c` | `drm_file` | si el driver implementa `open` DRM | inmutable | un `struct file` con dos `drm_file` |
| R-03 | FD ↔ `drm_file` | **N:1** | fd → (vía R-02) | spec `drm-shared` | `drm_file` | `dup`/`fork`/herencia | — | dos FDs del mismo `drm_file` con `client_id` distinto |
| R-04 | `drm_file` → `client_id` | **1:1** | file → valor | `drm_file.c:142` | `u64` | siempre | asignación única en el core; sin reasignación observada | dos `drm_file` con el mismo `client_id` |
| R-05 | `drm_file` → `minor` | **N:1** | file → minor | `drm_file.c:144` | `drm_minor` | siempre | inmutable | un `drm_file` accesible desde dos nodos |
| R-06 | `minor` → `drm_device` | N:1 | minor → dev | `drm_file.h:82` | `drm_device` | siempre | inmutable | dos `drm_device` para un minor |
| R-07 | `drm_device` → PCI device | **1:0:1** | dev → dev | rama `dev_is_pci` | `pci_dev` | **ssi** `dev_is_pci` | inmutable | dispositivo PCI-backed sin `drm-pdev`, o no-PCI con él |
| R-08 | `drm_file` → `pid` | **1:1** | file → pid | `drm_file.c:143` | `struct pid` | siempre | **MUTABLE** salvo `was_master` (E-9) | `drm_file_update_pid` inoperante; o master siguiendo al usuario actual |
| R-09 | `drm_file` → `object_idr` | 1:N | file → idr | `drm_file.h`; `drm_gem.c:884` | GEM objects | siempre | **mutable** | un GEM object usado sin estar en el `object_idr` |
| R-10 | `drm_file` → `master` | **1:0:1** | file → master | `drm_file.h:266` | `drm_master` | solo tipo primario; **transferible** | **mutable** | master transferido sin `lessor`/`lessees`; o `was_master` limpiado |
| R-11 | `drm_file` → `driver_priv` | 1:1 | file → ptr | `drm_file.h` | opaco | driver-defined | opaca | `NOT_AVAILABLE` |
| R-12 | `drm_file` → memory stats | 1:0:1 | file → agregado | `drm_print_memory_stats` | agregado | **por driver** | derivado | clave de memoria por proceso en la spec |
| R-13 | `drm_file` → engine stats | 1:0:N | file → contadores | spec `:79-133` | contador×engine | **por driver** | **no monótona** | `drm-engine-*` por proceso, o declarada monótona |
| R-14 | `VM` → `PASID` | `UNKNOWN` | — | `SOURCE_INCOMPLETE` | `PASID` | — | — | `NOT_AVAILABLE` |
| R-15 | `PASID` → proceso | **1:0:1** | pasid → proceso | docs amdgpu | proceso | **solo durante un page fault Y solo si el proceso está activo** | episódica | `PASID` impreso con PID sin fault concurrente |
| R-16 | `drm_file` → `driver_priv` → `amdgpu_fpriv` | **`UNKNOWN`** | — | `SOURCE_INCOMPLETE` | — | — | — | `NOT_AVAILABLE` |

### 3.1 Cadena `drm_file → driver_priv → amdgpu_fpriv → VM → PASID → proceso`, tramo a tramo

| Tramo | Estado |
|---|---|
| `drm_file` → `driver_priv` | **`ESTABLISHED`** — el campo existe (`drm_file.h`) |
| `driver_priv` → `amdgpu_fpriv` | **`SOURCE_INCOMPLETE`** — falta `amdgpu_drv.h` |
| `amdgpu_fpriv` → `VM` | **`SOURCE_INCOMPLETE`** |
| `VM` → `PASID` | **`SOURCE_INCOMPLETE`** |
| `PASID` → proceso | **`ESTABLISHED` solo como afirmación documental** y **condicional** (fault + proceso activo) |

**La cadena está rota en el tramo 2.** No se inventa semántica para cerrarla.

### 3.2 Equivalencias prohibidas — ninguna asumida

| Prohibida | `STATUS` |
|---|---|
| `FD == struct file` | **`NOT_COLLAPSED`** — R-01 es N:1, no 1:1 |
| `struct file == drm_file` | **`NOT_COLLAPSED`** — son tipos distintos con una relación 1:1 (R-02) |
| `drm-client-id == FD` | **`NOT_COLLAPSED`** — R-03 es N:1 |
| `drm-client-id == PID` | **`NOT_COLLAPSED`** — R-04 frente a R-08: `u64` con una única asignación en el core frente a `struct pid` que el core reasigna |
| `drm-client-id == PASID` | **`NOT_COLLAPSED`** —uno es `u64` monotónico global, otro un vmid |
| `drm-client-id == GPU page-fault client-id` | **`NOT_COLLAPSED`** — E-4 frente a E-17 → `C-1` |
| `drm-pdev == client identity` | **`NOT_COLLAPSED`** — E-5: constante por dispositivo; participa en identidad **solo** con unicidad por dispositivo (§4) |
| `PASID == client identity` | **`NOT_COLLAPSED`** — E-16: espacio de direcciones |
| `PASID == PID` | **`NOT_COLLAPSED`** — R-15 es condicional y episódica |
| `GEM object == process` | **`NOT_COLLAPSED`** — R-09 + R-08 sería `INFERENCE`, no relación declarada |
| `GEM object == drm_file` | **`NOT_COLLAPSED`** — el GEM object pertenece a un `object_idr` **de** un `drm_file`; no es un `drm_file` |
| `engine stats == process` | **`NOT_COLLAPSED`** — R-13: unidad declarada `drm_file` |
| `drm_master == drm-client-id` | **`NOT_COLLAPSED`** — E-10: capacidad transferible frente a `u64` de fichero |
| `card_clients == cantidad de FDs` | **`NAME_NOT_EVIDENCE`** — el nombre no es evidencia de su unidad. `PROJECT_MAPPING = NOT_ATTEMPTED`: el modelo técnico **no** afirma qué cuenta ni qué debería contar |
| `card_clients == cantidad de procesos` | **`NAME_NOT_EVIDENCE`** — ídem |

**Ninguna de estas 15 se convierte en identidad universal.** Si alguna se demostrara, se
documentaría como relación explícita con fuente y condiciones.

---

## 4 · `drm-client-id` — UNICIDAD

| Pregunta | Respuesta | `PROVENANCE` |
|---|---|---|
| ¿Qué identifica? | Un **fichero abierto DRM** (`drm_file`) | `PRIMARY_KERNEL_SOURCE` |
| ¿Qué unidad? | `drm_file`. No FD, no proceso, no master, no bloque de hardware | `PRIMARY_KERNEL_SOURCE` |
| **A) Unicidad global** | **Permitida** por la spec. La **implementación inspeccionada** la cumple: `ident` es un `atomic64` estático de módulo, incrementado una vez por `drm_file_alloc` → global en la práctica | `EXTERNAL_SPEC` (permiso) + `PRIMARY_KERNEL_SOURCE` (implementación) |
| **B) Unicidad por dispositivo** | **Permitida** por la spec: *"either globally unique, or unique within the scope of each device, in which case `drm-pdev` shall be present as well"* | `EXTERNAL_SPEC` (`:70-72`) |
| ¿Cuándo entra `drm-pdev`? | **Solo en B.** En A no participa de la identidad. Y en ambos casos `drm-pdev` **no discrimina por sí mismo** | `EXTERNAL_SPEC` + `PRIMARY_KERNEL_SOURCE` |
| ¿Estable en la vida del `drm_file`? | **Sí**: asignada una vez, sin reasignación; el contador no se reutiliza. **Distinto de `pid`, que es mutable** | `PRIMARY_KERNEL_SOURCE` |
| Generalización | **PROHIBIDA**: que la implementación observada sea global **no** convierte "global" en regla del modelo. Un consumidor debe tolerar B | — |

---

## 5 · OBSERVABILIDAD

`EXPOSED_BY_SYSTEM` → `READABLE_BY_ANALYZER` → `OBSERVED_IN_SAMPLE` → `PROVES_PROPERTY` →
`SATISFIES_PROJECT_REQUIREMENT`; y `PRESENCE` → `VALUE` → `DISCRIMINATION` → `ATTRIBUTION`.
Ninguna capa demuestra la siguiente.

| Dato | `SYSTEM_EXPOSES` | `ANALYZER_CAN_READ` | `ANALYZER_CURRENTLY_OBSERVES` | `PROPERTY_PROVEN` | `LIMITATION` |
|---|---|---|---|---|---|
| tabla de FD de un proceso | sí | sí | sí | completitud de la tabla, **en ese instante** | "no existe" e "ilegible" **no** se distinguen desde el symlink |
| `drm-driver` | **core**, incondicional | sí | sí | que el driver usó el helper del core | — |
| `drm-client-id` | **core**, incondicional | sí (texto) | **presencia, no valor** | **solo `PRESENCE`** | observar la clave **no** prueba discriminantes ni relación con proceso |
| `drm-pdev` | **core**, ssi PCI | sí (texto) | presencia | **BDF del dispositivo**, no identidad de cliente | **no** transporta vendor/device/class |
| `drm-master` | ioctl | no (ausente de fdinfo) | no | nada desde esta superficie | **transferible**; no es identidad de proceso |
| GEM object individual | **no** | no | no | nada | solo el **agregado** se expone |
| memory stats | **driver** | parcial | no | agregado **por cliente**, si el driver cumple | el core **no** lo garantiza; `=0` no prueba no-uso |
| engine stats | **driver** | no | no | `>0` ⇒ trabajo de ese `drm_file`; **`=0` no prueba nada** | **no monótona**; requiere retener el máximo |
| `drm_file.pid` | **no** | no directamente | solo vía `/proc/<pid>/fd` | el **FD poseído ahora**, proxy del campo | no cubre el caso master (pid del apertor) |
| `driver_priv` | **no** | no | no | nada | `UNKNOWN`, **no** vacío |
| `VM` / `PASID` | `UNKNOWN` | no | no | nada | `SOURCE_INCOMPLETE` |
| page-fault `client-id` | `UNKNOWN` | no | no | nada | `SOURCE_INCOMPLETE` |

**Hecho transversal**: el core expone **exactamente 3 claves** (`drm-driver`, `drm-client-id`,
`drm-pdev`); todo lo demás depende de `dev->driver->show_fdinfo`. La presencia de cualquier clave de
estadísticas es **atribución del driver**, no del core.

### 5.1 Ausencia

| Causa | Cómo se distinguiría |
|---|---|
| objeto realmente ausente | conocimiento de la interfaz del objeto |
| objeto no observado | cobertura del barrido |
| observación incompleta | registro de truncamiento |
| atributo no expuesto | la interfaz no lo publica |
| evidencia no accesible | registro de error/permiso |
| atributo requerido pero ausente | el criterio lo exige explícitamente |

**`INDISTINGUISHABLE_FROM_AVAILABLE_EVIDENCE`**: *"clave opcional no exportada"* y *"el driver no
usa `drm_show_fdinfo()`"*. Con el texto de fdinfo como única evidencia producen **la misma
observación**. **No se elige una**; es una cota de la evidencia, no un hecho del sistema.
**Ninguna ausencia se convierte en ausencia de propiedad.**

---

## 6 · CONFLICTOS

| ID | `SOURCE_A` | `SOURCE_B` | `WHY_CONFLICT` | `RESOLVED` | `FALSIFIER` |
|---|---|---|---|---|---|
| **C-1** | `drm_file.c:142` — `u64` global por `drm_file` | `drivers/gpu/drm/amdgpu/` — bloque de hardware en un fault (`SOURCE_INCOMPLETE`) | mismo nombre, **entidades distintas** | **`UNRESOLVED`**; la **no-identidad sí `ESTABLISHED`** por definición | fuente primaria que muestre que el page-fault `client-id` **es** `file->client_id` |
| **C-2** | `drm-usage-stats.rst:68` — `struct drm_file` | mismo fichero, `drm-engine-`/`drm-memory-` — *"this client"* (misma unidad, otro uso) | "client" designa **dos** unidades del core y **una** de amdgpu | **`UNRESOLVED`** | fuente que unifique ambas |
| **C-3** | plan del proyecto — atribución en fila separada | implementación del collector — atribución fusionada en la completitud | artefactos del **proyecto** | **`UNRESOLVED`**, y **no se resuelve aquí** (`PROJECT_MAPPING = NOT_ATTEMPTED`) | decisión humana documentada |
| **C-4** | `drm_file.c:142` — `atomic64` estático ⇒ **global** | `drm-usage-stats.rst:70-72` — **global o por dispositivo** | la implementación cumple la lectura global; la spec permite la otra | **`UNRESOLVED`** — **no se resuelve suponiendo que la implementación es la spec** | implementación asignada **por dispositivo** con `client-id` repetido y `drm-pdev` presente (spec-conformante) |

---

## 7 · `SOURCE_INCOMPLETE` — `P5` / `VM` / `PASID` / `driver_priv`(amdgpu)

- `SOURCE_INCOMPLETE` = `drivers/gpu/drm/amdgpu/` inaccesible por 3 mecanismos. Falta
  `amdgpu_drv.h` (que contendría `amdgpu_fpriv` con `vm` y `pasid`), `amdgpu_vm.h` (con
  `task_info`), y el punto donde se asigna `file->driver_priv`.
- **`WHAT_CAN_STILL_BE_ASSERTED`**: (a) `PASID` es un **vmid**; (b) su propósito declarado es
  enlazar vmid ↔ PID; (c) la impresión del proceso es **condicional** a que esté activo; (d)
  `driver_priv` **existe** en `struct drm_file`; (e) `PASID` y `drm-client-id` son **entidades
  distintas**; (f) `drm-pdev` y `drm_file.pid` **no dependen** de amdgpu.
- **`WHAT_CANNOT_BE_ASSERTED`**: (a) que exista relación `PASID ↔ drm_file`; (b) que exista
  `PASID ↔ client_id`; (c) que `PASID` sirva como identidad de nada; (d) el contenido de
  `driver_priv` para amdgpu; (e) cardinalidad o lifetime de `amdgpu_vm`.
- **Regla**: `SOURCE_INCOMPLETE` **no** se convierte en "la relación no existe". **No se busca más.**

---

## 8 · REVISIÓN DE AFIRMACIONES HISTÓRICAS

`AGENT_FORMALIZATION` salvo donde se indica. `PROJECT_MAPPING = NOT_ATTEMPTED`: se registra **qué
mide** un artefacto, **no** qué debería medir.

| `OLD_CLAIM` | `STATUS` | `WHY` | `CORRECTED_MODEL` | `SOURCE` |
|---|---|---|---|---|
| "attributable" es una propiedad técnica única | **`REFUTED`** | un término mezclaba propiedades distintas | §1.3: ocho grupos, nombres independientes | `AGENTS.md:176-177` + modelo |
| `DRM_ATTRIBUTION_FIELDS` agrupa la atribución | **`NAME_NOT_EVIDENCE`** | tuples de campos de **relaciones distintas** bajo un criterio | cada campo pertenece a su grupo (§1.3) | `collector:1033` |
| `card_clients` / `render_clients` cuentan clientes | **`NAME_NOT_EVIDENCE`** | el nombre no es evidencia de la unidad; el modelo técnico no afirma qué cuenta | `NAME_NOT_EVIDENCE` en §3.2 | `collector:2869-2870` |
| `drm_fds_enumerated` es una propiedad | **`REFUTED` como tal** | agrupa enumeración y atribución **pooled** en un valor | enumeración (grupo 8) y atribución (grupo 1) son distintas | `collector:1576` |
| `card_node_complete` / `render_node_complete` miden una propiedad | **`REFUTED` como descripción** | la expresión computa completitud **y** un predicado de atribución no definido | completitud (grupos 2 y 8) y atribución (grupo 1) son distintas | `collector:1557-1558`, `:2839-2840` |
| PASID es identidad de cliente | **`REFUTED`** | es un vmid; su relación con proceso es condicional y episódica | E-16 | `EXTERNAL_SPEC` |
| `drm-client-id` es identidad de FD | **`REFUTED`** | R-03 es N:1 | E-4, R-03 | `drm_file.c:142` |
| `drm-client-id` es identidad de PID | **`REFUTED`** | `u64` con una única asignación en el core frente a `struct pid` que el core reasigna | E-4 frente a E-9 | `drm_file.c:142` / `:143` |
| `drm-pdev` identifica el cliente | **`REFUTED`** | es constante por dispositivo | E-5; participa en identidad solo con unicidad por dispositivo | `drm_show_fdinfo` |
| `drm-pdev` es redundante | **`REFUTED`** | la spec permite unicidad por dispositivo, donde es **necesario** | §4 (B) | `:70-72` |
| page-fault `client-id` = `drm-client-id` | **`REFUTED`** como identidad | entidades distintas | E-17, `C-1` | `SOURCE_INCOMPLETE` |
| GEM object = proceso | **`REFUTED`** | R-09+R-08 sería `INFERENCE`, no relación declarada | §3.2 | `drm_gem.c:884` |
| engine stats = proceso | **`REFUTED`** | la unidad declarada es `drm_file` | E-13, R-13 | `:79-133` |
| memory stats = inventario de objetos | **`REFUTED`** | `drm_print_memory_stats` recibe un agregado pre-computado | E-12 | `drm_file.c` |
| `drm_memory_stats` las produce el core | **`REFUTED`** | el core solo las formatea; las imprime el driver | E-12, `drm_show_fdinfo` | `drm_file.c` |
| Implementación global ⇒ spec global | **`REFUTED`** | generalización de una implementación a la spec | §4, `C-4` | `:70-72` |

**Ninguna se reutiliza. Ninguna se corrige en código todavía.**

---

## 9 · CIERRE

```
TECHNICAL_MODEL_STATUS   = CLOSED
TECHNICAL_MODEL_VERSION  = 3.0
SOURCE_COVERAGE          = core DRM completo (11 ficheros, linux v6.12);
                           amdgpu = SOURCE_INCOMPLETE (3 mecanismos)
SOURCE_INCOMPLETE        = drivers/gpu/drm/amdgpu/**  ->  R-14, R-16, E-15, E-17,
                           y el tramo 2 de la cadena §3.1
ESTABLISHED_ENTITIES     = E-1..E-14 (14)   [E-15, E-17 = SOURCE_INCOMPLETE; E-16 = EXTERNAL_SPEC]
ESTABLISHED_RELATIONS    = R-01..R-10, R-12, R-13, R-15
PARTIAL_RELATIONS        = R-12, R-13 (la unidad la afirma la spec; el core no la produce)
UNKNOWN_RELATIONS        = R-14, R-16
CONFLICTS                = C-1, C-2, C-4 UNRESOLVED (tecnicos); C-3 UNRESOLVED (proyecto)
FALSIFIERS               = 18 formulados; NOT_AVAILABLE: R-11, R-14, R-16, E-14, E-15
PROJECT_MAPPING          = NOT_ATTEMPTED
BLOCKED_BY_SCOPE         = ninguno (todo lo independiente se cerro sin ejecucion)
```

**Criterio de cierre**: entidades con significado independiente ✓ · relaciones explícitas ✓ ·
equivalencias prohibidas separadas ✓ · conflictos registrados ✓ · `UNKNOWN`/`SOURCE_INCOMPLETE`
delimitados ✓ · falsificadores principales ✓ · procedencia registrada ✓ · **ninguna decisión
normativa dentro del modelo técnico** ✓.

**No se añadió ninguna capa**: el §1.3 agrupa, no subdivide; no se añadieron taxonomías, agentes ni
fases. La única subdivisión nueva es la de las claves de memoria (E-12), porque `drm-memory-<region>`
existe en la spec y **no** la emite el helper del core, lo que hace la distinción observable.

**La investigación técnica termina aquí.** Lo único no cerrado es la semántica humana de
`complete attributable evidence`, que no es una cuestión de kernel y pertenece a una fase
normativa posterior con su propia autorización.

## 10 · LO QUE ESTA RONDA NO HIZO

No modificó código, tests, `AGENTS.md`, `README` ni documentación del proyecto · no ejecutó C1,
`--run`, sudo, systemctl, runtime, benchmarks, tuning, ni cambios en GPU, sysfs, PM/governor o
storage · no commiteó · no creó agentes · no buscó más fuentes de amdgpu · no decidió `any`/`all`,
PASS/FAIL, campos obligatorios, `OWNERSHIP=FULL` ni qué debe cambiar el collector.
