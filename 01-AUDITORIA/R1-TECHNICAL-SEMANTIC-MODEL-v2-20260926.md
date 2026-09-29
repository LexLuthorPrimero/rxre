# R1-TECHNICAL-SEMANTIC-MODEL-20260926 · v2 CONSOLIDADO

`TECHNICAL_MODEL_VERSION` = **2.0** · `TECHNICAL_MODEL_STATUS` = **`CLOSED_WITH_DECLARED_LIMITS`**
Continuación y consolidación de `R1-TECHNICAL-SEMANTIC-MODEL-20260926.md` (v1). v2 lo **suplementa**
y marca sus correcciones; no lo reescribe. v1 queda `HISTORICAL`.

`PROJECT_MAPPING` = **`NOT_ATTEMPTED`** (ver §12)
`IMPLEMENTATION_CHANGE_REQUIRED` = **`YES`** — ver §12.1
`CODE_CHANGE_ALLOWED` = `NO` · nada implementado, modificado ni commiteado.

**Alcance**: responde solo *"¿qué entidades, atributos y relaciones están definidas por las fuentes
primarias de Linux DRM y qué puede observarse de ellas?"*. **No** decide el significado de
`complete attributable evidence`. **No** convierte ninguna propiedad técnica en requisito.

`TEMPORALITY` = `linux` v6.12 mainline, descargado y leído en esta sesión · `HOST_SCOPE` = ninguno
(este documento no contiene ninguna lectura del host RX550).

---

## 0 · `SOURCE_COVERAGE`

| Fuente | Estado | Contribución principal |
|---|---|---|
| `drivers/gpu/drm/drm_file.c` (996 L) | `OBTAINED` | `client_id`, `pid`, `minor`, `update_pid`, `show_fdinfo`, `print_memory_stats` |
| `include/drm/drm_file.h` | `OBTAINED` | `struct drm_file`, `struct drm_minor` |
| `drivers/gpu/drm/drm_lease.c` (733 L) | `OBTAINED` | `drm_master`, transferencia lessor/lessee |
| `drivers/gpu/drm/drm_auth.c` (467 L) | `OBTAINED` | `drm_master_check_perm`, razón de la excepción de pid |
| `include/drm/drm_lease.h` / `drm_auth.h` | `OBTAINED` | `struct drm_master` |
| `include/drm/drm_gem.h` (637 L) | `OBTAINED` | `struct drm_gem_object`, `refcount`, `handle_count` |
| `drivers/gpu/drm/drm_gem.c` (1535 L) | `OBTAINED` | iteración de `file->object_idr` |
| `include/drm/drm_drv.h` (554 L) | `OBTAINED` | `struct drm_device` |
| `drivers/gpu/drm/drm_internal.h` | `OBTAINED` | DRM interno |
| `Documentation/gpu/drm-usage-stats.rst` (189 L) | `OBTAINED` | spec de las claves fdinfo |
| `drivers/gpu/drm/amdgpu/**` | **`SOURCE_INCOMPLETE`** | 404 en `raw.githubusercontent`, en la API de contenidos de GitHub, y en `kernel.org/doc` |
| **`pasid` / `VM` / GPU page-fault `client-id`** | **`SOURCE_INCOMPLETE`** | sin fuente primaria del kernel accesible |

**Cobertura**: **todo el core DRM está cubierto**. Lo no cubierto es **exclusivamente el driver
amdgpu**. Ninguna afirmación de este documento depende de amdgpu.

---

## 1 · CAPAS DE SEPARACIÓN (regla transversal)

### 1.1 Cadena de observabilidad

| Capa | Definición | Lo que **no** autoriza afirmar |
|---|---|---|
| `EXPOSED_BY_SYSTEM` | el core o el driver publica el dato por alguna interfaz | que el analizador lo lea |
| `READABLE_BY_ANALYZER` | la lectura se completó sin error | que la lectura sea completa |
| `OBSERVED_IN_SAMPLE` | hubo valor en una ejecución concreta | que valga para otro instante |
| `PROVES_PROPERTY` | el dato, por sí, demuestra la propiedad técnica | que satisfaga un requisito |
| `SATISFIES_PROJECT_REQUIREMENT` | la propiedad cubre lo que un requisito pide | — |

**Regla**: `PROVES_PROPERTY` **no** se alcanza saltando una capa intermedia. Una capa ausente
deja la cadena rota en ese punto, y todo lo posterior es `NOT_ESTABLISHED`.

### 1.2 Cadena de capacidad de dato

| Nivel | Enunciado | Insumo | Relación con el anterior |
|---|---|---|---|
| `PRESENCE` | existe la clave en el texto | el texto | — |
| `VALUE` | se obtuvo el valor numérico | parseo del texto | **no implica** `PRESENCE`→`VALUE` automáticamente: exige un extractor |
| `DISCRIMINATION` | los valores permiten separar dos objetos | valores + no-unicidad resuelta | **no implica** `VALUE`→`DISCRIMINATION` sin conocer el alcance de la unicidad (§4) |
| `ATTRIBUTION` | se establece una relación con **otra entidad nombrada** | … + esa entidad | **no implica** `DISCRIMINATION`→`ATTRIBUTION`: falta nombrar el destino |

**Las cuatro son estrictamente crecientes en precondiciones. Ninguna se infiere de la anterior por
defecto.**

---

## 2 · MODELO DE ENTIDADES

`SOURCE` con `PRIMARY_KERNEL_SOURCE` = fichero:línea. `PROVENANCE` de toda la sección:
`PRIMARY_KERNEL_SOURCE`. Ninguna afirmación de §2 procede de documento del proyecto.

### E-1 · `FD` (file descriptor)
- `DEFINITION`: entrada de la tabla de descriptores de un proceso; el objeto que el usuario posee.
- `UNIT`: un descriptor.
- `SOURCE`: VFS (fuera del árbol DRM, no leído en esta ronda) · `PRIMARY_KERNEL_SOURCE` = Kernel, no DRM.
- `LIFETIME`: desde `open()` hasta `close()`; **`dup()`/`fork()` no crean un `struct file` nuevo**.
- `IDENTITY_SEMANTICS`: **ninguna identidad DRM**. No es `drm-client-id`; puede compartirlo.
- `MUTABILITY`: el FD puede cambiar de proceso por herencia; el `drm_file` que referencia, no.
- `OBSERVABILITY`: `EXPOSED` como `/proc/<pid>/fd/<n>`; `READABLE` como symlink.
- `KNOWN_LIMITS`: **el path `/proc/<pid>/fd/<n>` no distingue dos `drm_file` distintos**. Por tanto
  el path **no puede** ser la unidad de una relación de identidad.

### E-2 · `struct file` (`filp`)
- `DEFINITION`: objeto kernel de un fichero abierto; contiene `private_data`.
- `UNIT`: un `struct file`.
- `SOURCE`: `drm_file.c` — `struct drm_file *file = f->private_data;` (`drm_show_fdinfo`).
- `LIFETIME`: refcount por FD; liberado al último `fput`.
- `IDENTITY_SEMANTICS`: **`private_data` ↔ `drm_file` es 1:1**. Un `struct file` no puede
  referenciar dos `drm_file`.
- `MUTABILITY`: `private_data` no se reasigna.
- `OBSERVABILITY`: **no expuesto** por ninguna interfaz de usuario.
- `KNOWN_LIMITS`: su existencia solo es **inferible** por la relación 1:1 con `drm_file`.

### E-3 · `struct drm_file`
- `DEFINITION`: estado DRM por fichero abierto; "userspace client" según `drm-internals`.
- `UNIT`: **una apertura DRM** (no un FD, no un proceso).
- `SOURCE`: `drm_file.h` (`struct drm_file`) · asignación en `drm_file.c:142-144`.
- `LIFETIME`: `drm_file_alloc()` en la apertura; `drm_file_put` en el cierre. Nodo en
  `dev->filelist` mientras existe.
- `IDENTITY_SEMANTICS`: no tiene identidad propia comparable. Los campos que lo identifican
  externamente son `client_id` (estable) y `magic` (autenticación legacy).
- `MUTABILITY`: casi todos sus campos son mutables (`object_idr`, `master`, `pid`, `driver_priv`);
  `client_id` y `minor` **no**.
- `OBSERVABILITY`: **no expuesto directamente**; observable solo a través de las claves que lo
  resumen (`drm-client-id`, `drm-driver`, `drm-pdev`).
- `KNOWN_LIMITS`: su existencia como objeto **no** es observable si no se lee `drm-client-id`.

### E-4 · `drm-client-id`
- `DEFINITION`: clave fdinfo `Optional` cuyo propósito es *"distinguish duplicated and shared file
  descriptors"*.
- `UNIT`: un `drm_file`.
- `SOURCE`: `drm_file.c:142` `file->client_id = atomic64_inc_return(&ident);` ·
  spec `drm-usage-stats.rst:64-72`.
- `LIFETIME`: **asignada una vez**; existe mientras el `drm_file`.
- `IDENTITY_SEMANTICS`: **1:1 con `drm_file` por construcción en esta implementación**.
- `MUTABILITY`: **inmutable**. El contador `ident` es monotónico y no se reutiliza.
- `OBSERVABILITY`: `EXPOSED` **por el core** (incondicional dentro de `drm_show_fdinfo`).
- `KNOWN_LIMITS`: ver §4 completo. El core la emite; **quién la consume y con qué alcance de
  unicidad** es lo que la spec deja abierto.

### E-5 · `drm-pdev`
- `DEFINITION`: clave fdinfo `Optional`: *"the PCI **slot address** of the device in question"*.
- `UNIT`: un dispositivo PCI (formato `aaaa:bb.cc.d`).
- `SOURCE`: `drm_show_fdinfo` — `if (dev_is_pci(dev->dev))` con
  `dev = file->minor->dev`.
- `LIFETIME`: **no tiene**. **No se almacena**: se **deriva en el instante de imprimir**.
- `IDENTITY_SEMANTICS`: **identifica el DISPOSITIVO, no el cliente**. Es idéntico para todos los
  `drm_file` de un mismo dispositivo. **No identifica clientes.**
- `MUTABILITY`: no aplicable (valor derivado).
- `OBSERVABILITY`: `EXPOSED` **ssi** el dispositivo es PCI.
- `KNOWN_LIMITS`: **no incluye `vendor` ni `device`** — solo BDF. **No basta** para probar
  identidad de dispositivo por sí sola.

### E-6 · `struct drm_minor`
- `DEFINITION`: un nodo de dispositivo DRM (`/dev/dri/N`).
- `UNIT`: un nodo.
- `SOURCE`: `drm_file.h:77-87` — `index` (nº de minor), `type`, `kdev` (device Linux), `dev`.
- `LIFETIME`: registrada con el `drm_device`; sobrevive a todos sus `drm_file`.
- `IDENTITY_SEMANTICS`: identidad = (`index`, `type`).
- `MUTABILITY`: inmutable tras el registro.
- `OBSERVABILITY`: `EXPOSED` vía sysfs (`index`, `dev`); **el campo `index` es la ruta, no una
  identidad estable entre hosts**.
- `KNOWN_LIMITS`: **`cardN` no es identidad de dispositivo** — depende del orden de registro.

### E-7 · `struct drm_device`
- `DEFINITION`: estado de un driver+dispositivo.
- `UNIT`: un driver+dispositivo.
- `SOURCE`: `drm_drv.h` (`struct drm_device`) · relación `minor->dev` (`drm_file.h:82`).
- `LIFETIME`: probe → remove;|es padre de sus minors.
- `IDENTITY_SEMANTICS`: `struct device *dev` embebido.
- `MUTABILITY`: mayormente inmutable tras el probe; `filelist` es concurrente.
- `OBSERVABILITY`: `EXPOSED` vía sysfs.
- `KNOWN_LIMITS`: **no tiene identidad DRM serial**; solo la del `struct device`.

### E-8 · PCI device
- `DEFINITION`: dispositivo PCIe con BDF, `vendor`, `device`, `class`.
- `UNIT`: un dispositivo.
- `SOURCE`: rama `dev_is_pci(dev->dev)` + `to_pci_dev`.
- `LIFETIME`: registrar/desregistrar.
- `IDENTITY_SEMANTICS`: **BDF** — y es la única identidad de dispositivo portable entre hosts.
- `MUTABILITY`: inmutable.
- `OBSERVABILITY`: `EXPOSED` vía sysfs (`vendor`, `device`, `class`, BDF); `EXPOSED` **parcialmente**
  vía `drm-pdev` (**solo BDF**).
- `KNOWN_LIMITS`: `drm-pdev` **no** transporta `vendor`/`device`/`class`.

### E-9 · PID / TGID
- `DEFINITION`: `struct pid *` que representa el proceso que usa el `drm_file`.
- `UNIT`: un `task_struct` (identificado por TGID).
- `SOURCE`: `drm_file.c:143` `rcu_assign_pointer(file->pid, get_pid(task_tgid(current)));`
- `LIFETIME`: referencia `struct pid` con `get_pid`/`put_pid`.
- `IDENTITY_SEMANTICS`: **TGID, no PID de hilo**.
- `MUTABILITY`: **MUTABLE** por `drm_file_update_pid` (`rcu_replace_pointer`) —
  **con excepción**: `if (filp->was_master) return;`.
- `OBSERVABILITY`: **`drm_file.pid` NO se expone en fdinfo**. Observable **solo** por el path
  `/proc/<pid>/fd/<n>`, es decir, el **FD poseído ahora**, que es un proxy relacionado pero no idéntico.
- `KNOWN_LIMITS`: (a) la excepción master hace que el pid de un master sea **el del apertor
  original**; (b) el path `/proc` no es el campo `pid` del `drm_file`.

### E-10 · `struct drm_master`
- `DEFINITION`: propietario de recursos de display, con **identidad propia separada** del
  `drm_file`: `unique`, `magic_map`, `lessee_id`.
- `UNIT`: un master.
- `SOURCE`: `drm_lease.h` (`struct drm_master`) · `drm_lease.c` · `drm_auth.c:233-242`.
- `LIFETIME`: `kref`; **creado al obtener master, y transferible**:
  `lessee->lessor = drm_master_get(lessor)` (`drm_lease.c:247`).
- `IDENTITY_SEMANTICS`: **no es el `drm_file`**. Un `drm_file` puede tenerlo o no
  (`file->master`).
- `MUTABILITY`: **transferible por leasing**; `lessees` es una lista viva.
- `OBSERVABILITY`: `EXPOSED` por ioctl; **no por fdinfo**.
- `KNOWN_LIMITS`: **la propiedad de un master puede pasar de un proceso a otro** por leasing. Por
  tanto **master no es identidad estable de proceso**. Solo existe en nodos con `type` primario.

### E-11 · GEM object
- `DEFINITION`: objeto de buffer gestionado por GEM.
- `UNIT`: un `drm_gem_object`.
- `SOURCE`: `drm_gem.h` (`struct drm_gem_object`: `refcount` `kref`, `handle_count`, `dev`, `list`).
- `LIFETIME`: `refcount`; vive mientras alguien lo referencia.
- `IDENTITY_SEMANTICS`: **no tiene identidad propia observable**; se referencia por
  **handle numérico dentro de un `object_idr`**, y ese idr **pertenece a un `drm_file`**.
- `MUTABILITY`: handles alta/baja; `handle_count` varía.
- `OBSERVABILITY`: `EXPOSED` **agregado** por `drm_print_memory_stats`, que recibe un
  `drm_memory_stats` **pre-agregado**; la iteración de `file->object_idr` ocurre en el **llamante**
  (`drm_gem.c:884`). **El objeto individual no se expone.**
- `KNOWN_LIMITS`: `handle_count` cuenta **handles**, y un handle es por `drm_file`; por eso la spec
  define `drm-shared` como *"shared with another **file** (e.g., have more than a single handle)"*.

### E-12 · memory statistics
- `DEFINITION`: *"the amount of storage currently consumed by the buffer objects **belong to this
  client**"*, por región.
- `UNIT`: **agregado por `drm_file`** (no por GEM object individual).
- `SOURCE`: `drm_file.c` `drm_print_memory_stats` (`total = private + shared`) ·
  spec `drm-usage-stats.rst:143-160`.
- `LIFETIME`: **derivada**, sin almacenamiento propio en el core.
- `IDENTITY_SEMANTICS`: la unidad declarada por la spec es **"this client"**.
- `MUTABILITY`: cambia con `object_idr`.
- `OBSERVABILITY`: `EXPOSED` **por el driver** (vía `dev->driver->show_fdinfo`), **no por el core**.
- `KNOWN_LIMITS`: **el core no las produce ni las valida**. Que la unidad sea el `drm_file` es una
  **afirmación de la spec**, que el driver puede satisfaction o no.

### E-13 · engine statistics
- `DEFINITION`: tiempo que un engine *"spent busy executing workloads **belonging to this
  client**"*.
- `UNIT`: `drm_file` × engine (`<keystr>` estable por engine).
- `SOURCE`: `drm-usage-stats.rst:79-92`.
- `LIFETIME`: **contador del driver**; no hay contador en el core.
- `IDENTITY_SEMANTICS`: unidad declarada = **cliente** (`drm_file`).
- `MUTABILITY`: **no monótona por diseño**: *"not required to be constantly monotonic"*; ante un
  valor menor, *"userspace is expected to stay with that larger previous value"*.
- `OBSERVABILITY`: `EXPOSED` **por el driver**, no por el core.
- `KNOWN_LIMITS`: **`=0` no implica no-uso** (puede ser un retroceso no recuperado). **`>0` sí implica**
  trabajo ejecutado *perteneciente a ese cliente*. Es **tiempo acumulado**, no actividad actual.

### E-14 · `driver_priv`
- `DEFINITION`: puntero `void *` opaco, por `drm_file`, definido por el driver.
- `UNIT`: un puntero.
- `SOURCE`: `drm_file.h` (`void *driver_priv;` en `struct drm_file` y en `struct drm_master`).
- `LIFETIME`: la del `drm_file`.
- `IDENTITY_SEMANTICS`: **ninguna** en el core.
- `MUTABILITY`: opaca.
- `OBSERVABILITY`: **`NOT_EXPOSED`**. Sin fuente primaria de amdgpu, su contenido es
  `UNKNOWN`, no "vacío".
- `KNOWN_LIMITS`: **no usar su nombre como prueba de lo que contiene**.

### E-15 · `VM` (espacio de direcciones GPU)
- `DEFINITION`: no establecida por fuente primaria accesible.
- `UNIT`: `UNKNOWN` · `SOURCE`: **`SOURCE_INCOMPLETE`** (`drivers/gpu/drm/amdgpu/` inaccesible).
- `LIFETIME`/`MUTABILITY`/`OBSERVABILITY`: `UNKNOWN`.
- `KNOWN_LIMITS`: **no puede afirmarse que exista una relación observable con `drm_file`**.
  `SOURCE_INCOMPLETE` **no** es "no existe la relación".

### E-16 · `PASID`
- `DEFINITION`: un **vmid**. Su propósito declarado es *"used to link a vmid to a system process
  id"*.
- `UNIT`: un vmid.
- `SOURCE`: documentación de amdgpu (**`EXTERNAL_SPEC`**, no kernel) · implementación
  **`SOURCE_INCOMPLETE`**.
- `LIFETIME`: `UNKNOWN` a nivel de fuente.
- `IDENTITY_SEMANTICS`: **identifica un espacio de direcciones**, no un fichero, ni un cliente, ni
  un proceso.
- `MUTABILITY`: `UNKNOWN`.
- `OBSERVABILITY`: **condicional y episódica** — *"If the process is active when the fault happens,
  the process information will be printed"*.
- `KNOWN_LIMITS`: **la relación con proceso existe solo durante un page fault y solo si el proceso
  está activo en ese instante**. No es una relación estable ni consultable.

### E-17 · GPU page-fault `client-id`
- `DEFINITION`: **entidad distinta de E-4**, propia de amdgpu: identifica **la unidad de hardware
  (GPU block) que causó el fault**, no un fichero abierto.
- `UNIT`: un bloque del motor (p. ej. `CPF`, `CPC`, `SDMA`, `VCN`, `JPEG`).
- `SOURCE`: **`SOURCE_INCOMPLETE`** — la implementación está en `drivers/gpu/drm/amdgpu/`, inaccesible
  por 3 mecanismos.
- `IDENTITY_SEMANTICS`: **bloque de hardware**, no `drm_file`.
- `KNOWN_LIMITS`: **el nombre colisiona con E-4 y no significa lo mismo**. Ver `C-1`.

---

## 3 · MODELO DE RELACIONES

`SOURCE` = fichero:línea. `CARDINALITY` en la dirección indicada.

| ID | `RELATION` | `CARDINALITY` | `DIRECTION` | `SOURCE` | `TARGET` | `CONDITIONS` | `MUTABILITY` | `FALSIFIER` |
|---|---|---|---|---|---|---|---|---|
| **R-01** | FD → `struct file` | N:1 | fd → file | VFS (fuera de alcance) | `struct file` | siempre | refcount | dos FDs con distinto `struct file` para el mismo fichero abierto |
| **R-02** | `struct file` → `drm_file` | **1:1** | file → private_data | `drm_file.c` `f->private_data` | `drm_file` | si el driver implementa `open` DRM | inmutable | un `struct file` con dos `drm_file`, o un `drm_file` compartido por dos `struct file` |
| **R-03** | FD ↔ `drm_file` | **N:1** | fd → (vía R-02) | spec `drm-shared` *"more than a single handle"* | `drm_file` | `dup`/`fork`/herencia | — | dos FDs del mismo `drm_file` con `client_id` distintos |
| **R-04** | `drm_file` → `client_id` | **1:1** | file → valor | `drm_file.c:142` | `u64` | siempre | **inmutable** | dos `drm_file` con el mismo `client_id` |
| **R-05** | `drm_file` → `minor` | **N:1** | file → minor | `drm_file.c:144` | `drm_minor` | siempre | inmutable | un `drm_file` accesible desde dos nodos |
| **R-06** | `minor` → `drm_device` | N:1 | minor → dev | `drm_file.h:82` | `drm_device` | siempre | inmutable | dos `drm_device` para un minor |
| **R-07** | `drm_device` → PCI device | **1:0:1** | dev → dev | rama `dev_is_pci` | `pci_dev` | **ssi** `dev_is_pci` | inmutable | un dispositivo PCI-backed sin `drm-pdev`, o uno no-PCI con él |
| **R-08** | `drm_file` → `pid` | **1:1** | file → pid | `drm_file.c:143` | `struct pid` | siempre | **MUTABLE** salvo `was_master` | `drm_file_update_pid` inoperante, o el pid de un master siguiendo al usuario actual |
| **R-09** | `drm_file` → `object_idr` | 1:N | file → idr | `drm_file.h`; `drm_gem.c:884` | GEM objects | siempre | **mutable** | un GEM object usado por un `drm_file` sin estar en su `object_idr` |
| **R-10** | `drm_file` → `master` | **1:0:1** | file → master | `drm_file.h` | `drm_master` | solo nodos con master; **transferible** | **mutable** (leasing) | un master transferido sin `lessor`, o `lessor` sin `lessees` |
| **R-11** | `drm_file` → `driver_priv` | 1:1 | file → ptr | `drm_file.h` | opaco | driver-defined | opaca | — (`FALSIFICATION_STATUS = NOT_AVAILABLE`: contenido no definido) |
| **R-12** | `drm_file` → memory stats | 1:0:1 | file → agregado | `drm_print_memory_stats` | agregado | **por driver** | derivado | — (`NOT_AVAILABLE`: el core no la produce) |
| **R-13** | `drm_file` → engine stats | 1:0:N | file → contadores | spec `:79-92` | contador×engine | **por driver** | **no monótona** | — (`NOT_AVAILABLE`: el core no la produce) |
| **R-14** | `VM` → `PASID` | `UNKNOWN` | — | `SOURCE_INCOMPLETE` | `PASID` | — | — | `SOURCE_INCOMPLETE` |
| **R-15** | `PASID` → proceso | **1:0:1** | pasid → proceso | docs amdgpu | proceso | **solo durante un page fault Y solo si el proceso está activo** | episódica | un `PASID` impreso con un PID sin page fault concurrente |

### 3.1 Relaciones explícitamente **no** afirmadas

`client_id = FD` · `client_id = PID` · `client_id = proceso` · `client_id = GPU page-fault
client-id` · `PASID = client_id` · `PASID = PID` · `GEM object = proceso` · `engine stats = proceso`
· `memory stats = proceso` · `drm-master = proceso` (es **transferible**, §E-10) ·
`drm-pdev = identidad de cliente` · `drm-pdev = identidad de dispositivo completa` (solo BDF).

Ninguna se usa en este documento. No se cierran artificialmente.

### 3.2 Cadenas: cuáles están completas y cuáles no

| Cadena | Estado |
|---|---|
| FD → `struct file` → `drm_file` → `client_id` | **`COMPLETA`** (R-01..R-04) |
| FD → `drm_file` → `minor` → `drm_device` → PCI | **`COMPLETA`** (R-03, R-05..R-07) — con la salvedad de que `drm-pdev` solo aporta BDF |
| `drm_file` → `pid` | **`COMPLETA`** pero **volátil y con excepción** (R-08) |
| `drm_file` → memory/engine stats | **CONDICIONAL**: la unidad la afirma la spec; el core no la garantiza (R-12, R-13) |
| `drm_file` → GEM → proceso | **ABIERTA**: R-09 + R-08 composición plausible, **no declarada** por el core → `INFERRED` |
| `PASID` ↔ `drm_file` / `client_id` | **ABIERTA** — sin fuente primaria → `SOURCE_INCOMPLETE` |
| page-fault `client-id` ↔ `drm_file` | **ABIERTA** → `SOURCE_INCOMPLETE`; y **por definición no es la misma entidad** |

---

## 4 · `drm-client-id` — PUNTO CRÍTICO

| # | Pregunta | Respuesta | `PROVENANCE` |
|---|---|---|---|
| 1 | **¿Qué identifica?** | Un **fichero abierto DRM** (`drm_file`), para *"distinguish duplicated and shared file descriptors"* | `PRIMARY_KERNEL_SOURCE` (`drm_file.c:142`) + spec `:64-68` |
| 2 | **¿Qué unidad representa?** | `drm_file`. **No** FD, **no** proceso, **no** `drm_master`, **no** bloque de hardware | `PRIMARY_KERNEL_SOURCE` |
| 3 | **¿Qué significa su unicidad?** | La spec admite **dos** lecturas: **global**, o **única dentro del ámbito de cada dispositivo**, *"in which case `drm-pdev` shall be present as well"* | `EXTERNAL_SPEC` (`:70-72`) |
| 4 | **Global vs por dispositivo** | La **implementación actual** es global: `ident` es un `atomic64` estático de módulo, incremented una vez por `drm_file` → global en la práctica. Pero **eso es una implementación, no la spec** | `PRIMARY_KERNEL_SOURCE` (impl) · `EXTERNAL_SPEC` (permiso) |
| 5 | **¿Cuándo `drm-pdev` entra en el criterio?** | **Solo en el caso de unicidad por dispositivo** (punto 3). En el caso global, `drm-pdev` **no participa** de la identidad. Además `drm-pdev` **no discrimina** por sí mismo: es constante por dispositivo | `EXTERNAL_SPEC` + `PRIMARY_KERNEL_SOURCE` |
| 6 | **¿Estable durante la vida del `drm_file`?** | **Sí**: asignada una vez en `drm_file_alloc`, sin reasignación en el core. El contador no se reutiliza. **Distinto de `pid`, que sí es mutable** | `PRIMARY_KERNEL_SOURCE` |
| 7 | **Evidencia primaria de cada punto** | (1,2,6) `drm_file.c:142` · (3,4,5) `drm-usage-stats.rst:64-72` · (4-impl) `atomic64_inc_return(&ident)` · (5-no discrimina) derivación en `drm_show_fdinfo` desde `file->minor->dev->dev` | — |

**Regla aplicada**: el punto 4 demuestra que la **implementación** es global. **No** se extiende a
"la spec exige unicidad global". Ver `C-4` y error previo **#8**.

---

## 5 · MODELO DE ATRIBUCIÓN (técnico, no de proyecto)

Relaciones técnicas que **sí** existen, con su cardinalidad, y **sin** destino de proyecto:

`FD → drm_file` (R-03, N:1) · `drm_file → client_id` (R-04, 1:1, inmutable) · `drm_file → minor`
(R-05, N:1) · `minor → drm_device` (R-06) · `drm_device → PCI device` (R-07, condicional) ·
`drm_file → PID` (R-08, 1:1, **mutable salvo master**) · `PASID → proceso` (R-15, **solo durante un
page fault y solo si el proceso está activo**) · `GEM → drm_file` (R-09, 1:N, **por `object_idr`
del file**) · `engine stats → cliente` (R-13, **según spec; por driver, no por core**).

**Lo que este modelo NO hace**: no nombra un destinatario de atribución. `ATTRIBUTION` (nivel 4 de
§1.2) queda **`NOT_DEFINED`** en el modelo técnico, porque definirlo exigiría el requisito del
proyecto — que queda fuera de alcance por instrucción.

**Cadena de capacidad alcanzada por el analizador actual**: `PRESENCE` sí · `VALUE` **no** ·
`DISCRIMINATION` **no** · `ATTRIBUTION` **no definido**. El salto `PRESENCE → VALUE` está bloqueado
por diseño declarado del extractor (presencia, nunca valor). El salto `VALUE → DISCRIMINATION`
depende además del punto 3 de §4, que la spec deja abierto.

---

## 6 · OBSERVABILIDAD POR DATO

| Dato | `SYSTEM_EXPOSES` | `ANALYZER_CAN_READ` | `ANALYZER_CURRENTLY_OBSERVES` | `PROPERTY_PROVEN` | `LIMITATION` |
|---|---|---|---|---|---|
| tabla de FD de un proceso | sí (`/proc/<pid>/fd`) | sí | sí | completitud de la tabla, **en ese instante** | un FD resuelto como "no existe" y uno ilegible **no son distinguibles** desde el symlink |
| `drm-driver` | **core**, incondicional | sí | sí | que el driver usó el helper del core | — |
| `drm-client-id` | **core**, incondicional | sí (texto) | **presencia, no valor** | **solo `PRESENCE`** | observar la clave **no** prueba discriminantes ni relación con proceso |
| `drm-pdev` | **core**, ssi PCI | sí (texto) | sí (presencia) | **BDF del dispositivo**, no identidad de cliente | **no** transporta vendor/device/class |
| `drm-master` | ioctl | no (no está en fdinfo) | no | nada desde esta superficie | **transferible**: no es identidad de proceso |
| GEM object individual | **no** | no | no | nada | solo el **agregado** se expone |
| memory stats | **driver** | sí (parcial) | no | agregado **por cliente**, si el driver cumple | el core **no** lo garantiza; `=0` no prueba no-uso |
| engine stats | **driver** | no | no | `>0` ⇒ trabajo de ese cliente; **`=0` no prueba nada** | **no monótona** por diseño; requiere retener el máximo |
| PID/TGID del `drm_file` | **no** (no está en fdinfo) | no directamente | solo vía `/proc/<pid>/fd` | el **FD poseído ahora**, que es un proxy, no el campo `pid` | no cubre el caso master (pid del apertor) |
| `VM` / `PASID` | `UNKNOWN` | no | no | nada | `SOURCE_INCOMPLETE` |
| `driver_priv` | **no** | no | no | nada | `UNKNOWN`, **no** vacío |
| page-fault `client-id` | `UNKNOWN` | no | no | nada | `SOURCE_INCOMPLETE` |

**Hecho transversal de la mayor importance**: el core expone **exactamente 3 claves**
(`drm-driver`, `drm-client-id`, `drm-pdev`) y **todo lo demás depende de
`dev->driver->show_fdinfo`**. Por tanto **la presencia de cualquier clave de estadísticas es
atribución del driver**, no del core. `PRIMARY_KERNEL_SOURCE` (`drm_show_fdinfo`).

### 6.1 Ausencia de una clave: taxonomía

| Causa distinguible | Fuente que la distinguiría |
|---|---|
| clave opcional no exportada por el driver | spec + conocimiento del driver |
| el driver no usa `drm_show_fdinfo()` | presencia/ausencia de `drm-driver` |
| lectura incompleta del texto | registro de truncamiento |
| el FD no existe / desapareció | tabla de FD del proceso |
| el objeto está fuera del universo observado | cobertura del barrido |
| fuente inaccesible | registro de error de lectura |
| causa desconocida | — |

**`INDISTINGUISHABLE_FROM_AVAILABLE_EVIDENCE`**: *"clave opcional no exportada"* y *"el driver no
usa `drm_show_fdinfo()`"*. Con el texto de fdinfo como única evidencia, **ambas producen exactamente
la misma observación** (ausencia de `drm-driver` y de las claves derivadas). **No se elige una.**
Es una cota de la evidencia disponible, no un hecho del sistema.

**Ninguna de las ausencias se convierte en ausencia de propiedad.**

---

## 7 · CONFLICTOS

### `C-1` · DRM `drm-client-id` vs GPU page-fault `client-id`
- `SOURCE_A`: `drm_file.c:142` — `u64` global por `drm_file`, identificador de fichero abierto.
- `SOURCE_B`: `drivers/gpu/drm/amdgpu/` — identificador de **bloque de hardware** en un page fault.
  `SOURCE_INCOMPLETE` para la implementación.
- `WHY_CONFLICT`: **mismo nombre, entidades distintas**; el nombre no discrimina.
- `RESOLVED` = **`UNRESOLVED`** (la fuente B no es accesible) — pero la **no-identidad está
  `ESTABLISHED`** por definición de ambas.
- `FALSIFIER`: una fuente primaria que muestre que el page-fault `client-id` **es** el
  `file->client_id`. `SOURCE_INCOMPLETE`; no se busca más.

### `C-2` · Tres sentidos de "client"
- `SOURCE_A`: `drm-usage-stats.rst:68` — *"in kernel representation of `struct drm_file`"*.
- `SOURCE_B`: el mismo fichero, `drm-engine-`/`drm-memory-` — *"this client"* (misma unidad, otro uso).
- `SOURCE_C`: amdgpu page-fault — bloque de hardware.
- `WHY_CONFLICT`: "client" designa **dos** unidades del core (una) y **una** de amdgpu (otra).
- `RESOLVED` = **`UNRESOLVED`**. `FALSIFIER`: fuente primaria que unifique las dos.

### `C-3` · Plan del proyecto vs implementación del collector
- `SOURCE_A`: plan del proyecto — atribución en fila separada.
- `SOURCE_B`: implementación del collector — atribución fusionada en la fila de completitud.
- `WHY_CONFLICT`: **artefactos del proyecto**. Registrado por completitud; **no se resuelve en este
  documento** (`PROJECT_MAPPING = NOT_ATTEMPTED`).
- `RESOLVED` = **`UNRESOLVED`**. `FALSIFIER`: decisión humana documentada.

### `C-4` · Unicidad global implementada vs unicidad global **o por dispositivo** permitida
- `SOURCE_A`: `drm_file.c:142` — `atomic64_inc_return(&ident)`, contador estático ⇒ **global**.
- `SOURCE_B`: `drm-usage-stats.rst:70-72` — *"either globally unique, or unique within the scope of
  each device, in which case `drm-pdev` shall be present as well"*.
- `WHY_CONFLICT`: la **implementación** cumple la lectura global; la **spec** permite también la
  otra. Un analizador que asuma global **no está violate la spec**, pero **no puede afirmar** que
  todo driver lo haga.
- `RESOLVED` = **`UNRESOLVED`** — y **no se resuelve asumiendo la implementación como spec**.
- `FALSIFIER`: una implementación asignada **por dispositivo** que emita `client_id` repetido en
  dispositivos distintos con `drm-pdev` presente. Tal implementación sería spec-conformante.

---

## 8 · `P5` / `VM` / `PASID` — `SOURCE_INCOMPLETE`

- `SOURCE_INCOMPLETE` = `drivers/gpu/drm/amdgpu/` inaccesible en `raw.githubusercontent`, en la API de
  contenidos de GitHub y en `kernel.org/doc` (3 mecanismos distintos). Falta además cualquier fuente
  kernel que enlace `amdgpu_vm`, `amdgpu_fpriv` y `amdgpu_pasid`.
- `WHAT_IS_MISSING`: la definición de `amdgpu_fpriv` (que contendría `vm` y `pasid`), de
  `amdgpu_vm` (con `task_info`), y el punto donde se asigna `file->driver_priv`.
- **`WHAT_CAN_STILL_BE_ASSERTED`**: (a) `PASID` es un **vmid** — `EXTERNAL_SPEC`; (b) su propósito
  declarado es **enlazar vmid ↔ PID durante un page fault** — `EXTERNAL_SPEC`; (c) la impresión del
  proceso es **condicional** a que el proceso esté activo en ese instante — `EXTERNAL_SPEC`;
  (d) `driver_priv` **existe** como campo en `struct drm_file` — `PRIMARY_KERNEL_SOURCE`;
  (e) **`PASID` es una entidad distinta de `drm-client-id`** — por definición de ambas.
- **`WHAT_CANNOT_BE_ASSERTED`**: (a) que exista una relación `PASID ↔ drm_file`; (b) que exista una
  relación `PASID ↔ client_id`; (c) que `PASID` pueda servir como identidad de nada; (d) el contenido
  de `driver_priv` para amdgpu; (e) cardinalidad o ciclo de vida de `amdgpu_vm`.
- **Regla**: `SOURCE_INCOMPLETE` **no** se convierte en "la relación no existe". Se convierte en
  "no se puede afirmar". **No se busca más.**

---

## 9 · FALSIFICACIÓN

| Afirmación | Falsificador concreto | `FALSIFICATION_STATUS` |
|---|---|---|
| R-02 1:1 file↔drm_file | un `struct file` con dos `drm_file`, o uno con dos `struct file` | **`AVAILABLE`** |
| R-03 N:1 FD↔drm_file | dos FDs del mismo `drm_file` con `client_id` distintos | **`AVAILABLE`** |
| R-04 1:1 e inmutable | dos `drm_file` con el mismo `client_id` | **`AVAILABLE`** |
| Unicidad de `client_id` (global) | una implementación que emita `client_id` repetido entre dispositivos, con `drm-pdev` presente | **`AVAILABLE`** (y sería spec-conformante → resolvería `C-4`) |
| R-05 N:1 drm_file→minor | un `drm_file` accesible desde dos nodos | **`AVAILABLE`** |
| R-08 `drm_file`→PID | `drm_file.pid` ausente para un `drm_file` vivo | **`AVAILABLE`** |
| R-08 mutabilidad | `drm_file_update_pid` inoperante, o el pid de un master siguiendo al usuario actual | **`AVAILABLE`** |
| Excepción master | un master cuyo `pid` se actualiza | **`AVAILABLE`** |
| R-07 / `drm-pdev`→dispositivo | un dispositivo PCI-backed sin `drm-pdev`, o uno no-PCI con él | **`AVAILABLE`** |
| `drm-pdev` no discrimina clientes | dos `drm_file` del mismo dispositivo con `drm-pdev` **distinto** | **`AVAILABLE`** |
| R-10 transferibilidad de master | un master transferido sin `lessor`/`lessees` | **`AVAILABLE`** |
| R-12 memory→cliente | una clave de memoria **por proceso** en la spec | **`AVAILABLE`** (hoy: la spec no la define) |
| R-13 engine→cliente | idem; o `drm-engine-*` definida por proceso | **`AVAILABLE`** |
| `engine = 0` no prueba no-uso | una `drm-engine-*` que documentase `0` como "sin trabajo" | **`AVAILABLE`** |
| R-15 PASID→proceso | un `PASID` impreso con PID sin page fault concurrente | **`AVAILABLE`** (pero la fuente es `SOURCE_INCOMPLETE`) |
| R-11 `driver_priv` | — | **`NOT_AVAILABLE`** (contenido no definido) |
| R-12/R-13 producidas por el core | — | **`NOT_AVAILABLE`** (el core **no** las produce: no hay afirmación que falsificar) |
| R-14 `VM`→`PASID` | — | **`NOT_AVAILABLE`** (`SOURCE_INCOMPLETE`) |

---

## 10 · `PROVENANCE`

| `PROVENANCE` | Alcance | Uso permitido |
|---|---|---|
| `PRIMARY_KERNEL_SOURCE` | todo §2, §3, §4, §6 salvo lo marcado `SOURCE_INCOMPLETE` | **semántica del kernel** |
| `EXTERNAL_SPEC` | `drm-usage-stats.rst`; docs de amdgpu | **interpretación técnica**; describe lo que la spec permite, no lo que toda implementación hace |
| `PROJECT_DOCUMENT` | — | **ausente por instrucción** en este documento |
| `AGENT_FORMALIZATION` | — | **ausente por instrucción** |
| `INFERENCE` | R-09+R-08 componiendo `GEM → proceso`; `PROPERTY_PROVEN` de la columna `/proc` | marcado como tal, nunca como semántica del kernel |

**Regla**: `PROJECT_DOCUMENT` y `AGENT_FORMALIZATION` **no aparecen como semántica del kernel** en
ninguna línea de este documento.

---

## 11 · REVISIÓN DE ERRORES ANTERIORES

| # | `OLD_CLAIM` | `WHY_WRONG_OR_INCOMPLETE` | `CORRECTED_MODEL` | `SOURCE` | `STATUS` |
|---|---|---|---|---|---|
| 1 | `drm-pdev` es identidad del cliente | es **constante por dispositivo**; se deriva en imprimir desde `file->minor->dev->dev`; idéntico para todos los `drm_file` del dispositivo | `drm-pdev` identifica **el dispositivo**; solo participa en la identidad si la unicidad es por dispositivo (§4.5) | `drm_file.c` `drm_show_fdinfo` | **`REFUTED`** |
| 2 | `drm-pdev` es simplemente redundante | la spec **permite** unicidad de `client_id` por dispositivo, y entonces `drm-pdev` **es necesario** | redundante **solo** bajo la lectura global; es **necesario** bajo la lectura por dispositivo → `C-4` | `drm-usage-stats.rst:70-72` | **`REFUTED`** |
| 3 | `client_id` = PID / proceso | son de naturaleza distinta: `u64` monotónico global e inmutable vs `struct pid` reasignable. `R-04` y `R-08` son relaciones distintas | `client_id` identifica **un `drm_file`**; el pid identifica **el proceso que lo usa ahora** | `drm_file.c:142` vs `:143` | **`REFUTED`** |
| 4 | page-fault `client-id` = DRM `drm-client-id` | **entidades distintas**: bloque de hardware vs fichero abierto | ambos se llaman "client" y **no** significan lo mismo → `C-1` | `SOURCE_INCOMPLETE` (amdgpu) | **`REFUTED`** como identidad; el **detalle** queda `SOURCE_INCOMPLETE` |
| 5 | PASID es identidad estable de cliente | es un **vmid**; su relación con proceso es **condicional y episódica** (page fault + proceso activo) | `PASID` es un espacio de direcciones, no una identidad de nada observable fuera de un fault | docs amdgpu (`EXTERNAL_SPEC`) | **`REFUTED`** |
| 6 | el FD es la unidad de cliente | varios FDs pueden compartir un `drm_file`; la spec lo dice con `drm-shared` *"more than a single handle"* | la unidad es el **`drm_file`** (R-03, N:1) | spec `:143-160` + `drm-shared` | **`REFUTED`** |
| 7 | las estadísticas de cliente son estadísticas de proceso | la spec define la unidad como *"this client"*; **el core no las produce**, las imprime el driver | son **por `drm_file`**, declaradas por la spec y **no garantizadas** por el core | `drm-usage-stats.rst:143-160`; `drm_file.c` | **`REFUTED`** |
| 8 | generalizar una implementación a la spec | `atomic64` estático ⇒ unicidad global **en esta implementación**; la spec **permite** por dispositivo | la spec manda; la implementación es **una** realization permitida | `:70-72` vs `drm_file.c:142` | **`REFUTED`** |
| 9 | convertir ausencia de dato en ausencia de propiedad | §6.1: hay ≥6 causas y **dos son indistinguibles** con la evidencia disponible | la ausencia se registra como **observación**, con sus causas candidatas, nunca como propiedad ausente | este doc §6.1 | **`REFUTED`** |

**Todos los nueve quedan `REFUTED` y corregidos en el modelo. Ninguno se reutiliza.**

---

## 12 · SALIDA FINAL

```
TECHNICAL_MODEL_STATUS   = CLOSED_WITH_DECLARED_LIMITS
TECHNICAL_MODEL_VERSION  = 2.0
SOURCE_COVERAGE          = core DRM completo (10 ficheros, linux v6.12);
                           amdgpu y page-fault client-id = SOURCE_INCOMPLETE
SOURCE_INCOMPLETE        = drivers/gpu/drm/amdgpu/**  (404 en 3 mecanismos);
                           consequentemente R-14 (VM->PASID) y la implementacion de
                           R-15 y de C-1 quedan sin fuente primaria
ESTABLISHED_ENTITIES     = E-1..E-14  (14)   [E-15..E-17 = SOURCE_INCOMPLETE]
ESTABLISHED_RELATIONS    = R-01..R-10     (10)
PARTIAL_RELATIONS        = R-11 (opaca), R-12, R-13 (spec las declara por cliente;
                           el core no las produce; las imprime el driver)
UNKNOWN_RELATIONS        = R-14 (VM->PASID)
CONFLICTS                = C-1 UNRESOLVED, C-2 UNRESOLVED, C-3 UNRESOLVED
                           (proyecto, no resuelto aqui), C-4 UNRESOLVED
FALSIFIERS               = 14 AVAILABLE, 4 NOT_AVAILABLE (R-11, R-12, R-13, R-14)
OBSERVABILITY_LIMITS     = el core expone 3 claves y todo lo demas depende del driver;
                           drm_file.pid NO se expone; el GEM object individual NO se expone;
                           drm-pdev NO transporta vendor/device; 2 causas de ausencia
                           INDISTINGUISHABLE_FROM_AVAILABLE_EVIDENCE
PROJECT_MAPPING          = NOT_ATTEMPTED
```

### 12.1 · `IMPLEMENTATION_CHANGE_REQUIRED = YES`

Ninguna conclusión de este modelo se implementó. Se registra que, **si** alguien quisiera llevar
`DISCRIMINATION` al analizador, haría falta: (a) un extractor que devuelva el **valor**, no la
presencia; (b) decidir el alcance de unicidad (§4.3) antes de decidir el criterio; (c) decidir si
`drm-pdev` entra en el criterio. **No se propone ninguno de los tres aquí** y **no se implementa
ninguno**.

### 12.2 · Lo que queda abierto, y es correcto que quede abierto

La única cuestión que este modelo técnico **no** puede cerrar es el **significado humano** de la
expresión normativa. No se resuelve técnicamente. El modelo técnico queda cerrado con sus límites
declarados; la semántica del requisito requiere una fuente que no es un fichero de kernel.

---

## 13 · LO QUE ESTA RONDA NO HIZO

No implementó `DISCRIMINATION` · no corrigió nombres ni conteos · no modificó `card_node_complete`,
`render_node_complete`, `card_clients`, `render_clients`, `drm_fds_enumerated` ni
`DRM_ATTRIBUTION_FIELDS` · no mapeó a `OWNERSHIP=FULL`, `G-1`, `G-2` ni `P3`–`P8` · no modificó
código, tests, `AGENTS.md`, `README`, documentación normativa, Git ni sistema · no ejecutó sudo,
systemctl, C1, runtime, benchmarks ni cambios de sysfs/GPU/PM/storage · no buscó más fuentes de
amdgpu · no inventó ninguna causa de ausencia.
