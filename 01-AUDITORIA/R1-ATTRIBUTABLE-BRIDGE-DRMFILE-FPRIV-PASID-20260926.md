# R1-ATTRIBUTABLE-BRIDGE-DRMFILE-FPRIV-PASID-20260926

`DOCUMENT_KIND = RESEARCH` · `NORMATIVE_STATUS = RESEARCH_ONLY`
No es requisito. No sustituye ni sobrescribe V2 ni documento anterior alguno.
`CODE_CHANGED = NO` · `COLLECTOR_CHANGED = NO` · `TESTS_CHANGED = NO` · `AGENTS.md = UNCHANGED`
`HOST_MEASUREMENT = NONE` · `COMMIT = NO`

> **CLASIFICACIÓN: `SOURCE_INCOMPLETE`.** La mitad DRM se verificó con código fuente primario.
> La mitad AMDGPU —donde estaría el puente— **no fue accesible**. No se infiere lo que no se leyó.

---

## 1 · EXECUTIVE_FINDING

Se obtuvo **código fuente primario del core DRM** (`drm_file.c`, `drm_gem.c`) y responde con
autoridad a dos de las tres preguntas finales. El subárbol `amdgpu/` resultó **inaccesible desde
este entorno en tres hosts distintos**, de modo que la cadena `drm_file → amdgpu_fpriv → VM → PASID
→ task_info` **no se puede afirmar ni desmentir**: no se leyó el código que la contendría.

Tres hallazgos con evidencia de código, que **corrigen** conclusiones previas:

1. **`drm-client-id` es un contador global por boot, no por dispositivo.**
   `static atomic64_t ident; file->client_id = atomic64_inc_return(&ident);`
   Es **monotónico global dentro de un boot** y **se reasigna en cada arranque**. La spec exige
   *"globally unique, or unique within the scope of each device"*; la implementación es **más fuerte
   que el mínimo**, pero **no estable en el tiempo**.

2. **`drm_file.pid` es MUTABLE.** `drm_file_update_pid()` hace
   `rcu_replace_pointer(filp->pid, pid, 1)` con `pid = task_tgid(current)`, y su comentario explica
   por qué: *"Master nodes need to keep the original ownership…"*. Es decir, **el PID de un
   `drm_file` puede reasignarse a otro proceso** (p. ej. por herencia/pasado de FD). El `client-id`
   observado en fdinfo pertenece a un `drm_file` cuyo `pid` **puede haber cambiado** desde el `open()`.

3. **`drm-pdev` se emite solo si el dispositivo es PCI.**
   `if (dev_is_pci(dev->dev)) { … drm_printf(&p, "drm-pdev:\t%04x:%02x:%02x.%d\n", …) }`
   Para un dispositivo PCI es **incondicional**; en uno no-PCI es **ausente por diseño**, no por
   lectura parcial.

---

## 2 · SOURCE_UNIVERSE

| ID | Archivo | URL | Estado |
|---|---|---|---|
| **K1** | `drivers/gpu/drm/drm_file.c` | `raw.githubusercontent.com/torvalds/linux/master/…` | **OBTENIDO** (integral) |
| **K2** | `drivers/gpu/drm/drm_gem.c` | ídem | **OBTENIDO** (integral) |
| K3 | `drivers/gpu/drm/amdgpu/amdgpu_drv.h` | ídem | **404** |
| K4 | `drivers/gpu/drm/amdgpu/amdgpu_vm.c` | ídem | **404** |
| K5 | `drivers/gpu/drm/amdgpu/amdgpu_gem.c` | ídem | **404** (no intentado; mismo directorio) |
| K6 | `drivers/gpu/drm/amdgpu/Makefile` | ídem | **404** |
| K7 | `drivers/gpu/drm/amd/include/asic_reg.h` | ídem | **404** |
| K8 | `drivers/gpu/drm/amdgpu/amdgpu_vm.c` (rama `v6.12`) | ídem | **404** |
| K9 | `drivers/gpu/drm/amdgpu/amdgpu_vm.c` | `cdn.jsdelivr.net/gh/torvalds/linux@master/…` | **404** |
| K10 | `drivers/gpu/drm/amdgpu/amdgpu_vm.c` | `github.com/torvalds/linux/raw/master/…` | **404** |
| K11 | `drivers/gpu/drm/amdgpu/*` (cualquier) | `git.kernel.org`, `elixir.bootlin.com` | **Anubis bot-wall** |
| K12 | `Documentation/process/coding-assistants.rst` | raw.githubusercontent | **OBTENIDO** |

### 2.1 Caracterización del bloqueo

`drivers/gpu/drm/drm_file.c` **OK** · `drivers/gpu/drm/drm_gem.c` **OK** ·
`Documentation/process/coding-assistants.rst` **OK** · `README` raíz **OK** ·
`drivers/gpu/drm/amdgpu/**` **404** · `drivers/gpu/drm/amd/**` **404**.

El bloqueo es **por subárbol de directorio**, reproducible en **3 hosts** (raw.githubusercontent,
jsdelivr, github.com/raw) y **2 ramas** (`master`, `v6.12`). No es transitorio ni de profundidad de
ruta. **No es un indicio de que esos archivos no existan.**

### 2.2 Nota de gobernanza (K12)

El kernel mantiene política explícita para asistentes de IA
(`Documentation/process/coding-assistants.rst`): *"AI agents **MUST NOT** add Signed-off-by tags.
Only humans can legally certify the Developer Certificate of Origin"*, y las contribuciones deben
llevar `Assisted-by:`. Regula **contribuir**, no leer. Se registra porque este proyecto podría
reportar upstream en el futuro y el DCO es una obligacion humana.

---

## 3 · DRM_FILE_ANALYSIS

**RELATION**: `drm_file → client_id`
`SOURCE`: K1 `drm_file_alloc()` · `SYMBOL`: `file->client_id` · `STRUCT/FIELD`: `u64 client_id`
`CREATED WHERE`: `drm_file_alloc()`, `static atomic64_t ident = ATOMIC64_INIT(0)` (file-scope static)
`ASSIGNED WHERE`: `file->client_id = atomic64_inc_return(&ident);` con el comentario
*"Get a unique identifier for fdinfo"*
`CONSUMED WHERE*: `drm_show_fdinfo()` → `drm_printf(&p, "drm-client-id:\t%llu\n", file->client_id)`;
`drm_file_err()` → `"client-id:%llu"`
`LIFETIME`: por `drm_file`; el contador, por boot
`IDENTITY UNIT`: **un `drm_file`**, es decir una apertura de nodo DRM
`DIRECT OR INFERRED`: **DIRECT**
`LIMITATION`: monotónico global por boot ⇒ **no comparable entre ventanas ni entre arranques**
`FALSIFIER`: que elIncremento no sea global o que se reasigne dentro de un boot
`CLASSIFICATION`: **`ESTABLISHED`**

**RELATION**: `drm_file → PID`
`SOURCE`: K1 · `ASSIGNED`: `rcu_assign_pointer(file->pid, get_pid(task_tgid(current)));`
`CONSUMED`: `drm_file_err()` → `pid_task(pid, PIDTYPE_TGID)`; `drm_file_update_pid()`
`IDENTITY UNIT`: **TGID = proceso, no hilo** (`task_tgid`)
`DIRECT OR INFERRED`: **DIRECT**

**RELATION**: `drm_file → PID` — **SEGUNDA ESCRITURA**
`SOURCE`: K1 `drm_file_update_pid()`
`EVIDENCE`:
```c
if (filp->was_master) return;
pid = task_tgid(current);
if (pid == rcu_access_pointer(filp->pid)) return;
old = rcu_replace_pointer(filp->pid, pid, 1);
```
`INTERPRETATION`: **el PID asociado a un `drm_file` no es inmutable**; se re-apunta al proceso
actual cuando otro toma el uso del descriptor
`LIMITATION`: no se observo quien lo invoca (el codigo de amdgpu no se leyo) → **cuando se
reasigna: `NOT_ESTABLISHED`**
`FALSIFIER`: que `drm_file_update_pid` no existiera o fuera no alcanzable
`CLASSIFICATION`: **`ESTABLISHED` (que es mutable)**; el disparador, `NOT_ESTABLISHED`

**RELATION**: `drm_file → minor` → `drm_device`
`SOURCE`: K1 `file->minor = minor;` y `dev = file->minor->dev`
`DIRECT`; `IDENTITY UNIT`: el minor (nodo)

**RELATION**: `drm_file → struct file`
`SOURCE`: K1 `drm_open_helper()`: `filp->private_data = priv; priv->filp = filp;`
`DIRECT`. Nótese la simetría: `filp->private_data` ↔ `priv->filp`.

**RELATION**: `drm_file → dev.filelist`
`SOURCE`: K1 `list_add(&priv->lhead, &dev->filelist);` bajo `dev->filelist_mutex`
`DIRECT`. `IDENTITY UNIT`: la lista de clientes del dispositivo.

---

## 4 · DRIVER_PRIV_ANALYSIS

`drm_file` tiene el campo `void *driver_priv` (documentado en `drm-internals`, V2/S3), y K1 **invoca
el callback del driver durante la construcción**:

```c
if (dev->driver->open) {
        ret = dev->driver->open(dev, file);
        …
}
```
dentro de `drm_file_alloc()`, **antes** de que `drm_open_helper()` devuelva.

**Lo que esto establece**: existe un punto de extensión por `drm_file` donde un driver cuelga datos
privados, y se invoca exactamente **una vez por `drm_file`**, en su creación.

**Lo que NO se establece**: que `driver_priv` apunte a `struct amdgpu_fpriv`. Eso solo se ve en el
código de amdgpu (`amdgpu_drv.h`, `amdgpu_main.c`), **inaccesible**.

`DIRECT OR INFERRED`: el **mecanismo** es `DIRECT`; el **tipo concreto** es `NOT_ESTABLISHED`.
`CLASSIFICATION`: **`NOT_ESTABLISHED`** para `driver_priv → amdgpu_fpriv`.

---

## 5 · AMDGPU_FPRIV_ANALYSIS

**Sin fuente.** `struct amdgpu_fpriv` no fue leído. No se afirma su existencia, sus campos, su
creación (`amdgpu_fpriv_init`/`amdgpu_file_priv`) ni su relación con `driver_priv`.

`CLASSIFICATION`: **`NOT_ESTABLISHED`** · `SOURCE`: **`NOT_AVAILABLE`**

## 6 · VM_ANALYSIS · 14 · TASK_INFO_ANALYSIS

**Sin fuente.** `struct amdgpu_vm`, `amdgpu_vm_init()`, `amdgpu_vm_set_task_info()`,
`amdgpu_vm_get_task_info_pasid()`, `amdgpu_vm_get_task_info_vm()` no fueron leídos.

Lo único que se sabe de la semántica de VM/PASID sigue siendo **documental** (V2/S4,
`amdgpu/debugging`): *"The pasid is used to link a vmid to a system process id. If the process is
active when the fault happens, the process information will be printed."*

`CLASSIFICATION`: **`NOT_ESTABLISHED`** · `SOURCE`: **`NOT_AVAILABLE`**

## 7 · PASID_ANALYSIS

| Pregunta | Respuesta | Base |
|---|---|---|
| Dónde se asigna el PASID | **`NOT_ESTABLISHED`** | fuente inaccesible |
| Qué estructura lo almacena | **`NOT_ESTABLISHED`** | ídem |
| ¿Pertenece a `fpriv` o a `VM`? | **`NOT_ESTABLISHED`** | ídem |
| ¿Varios VM por fpriv? | **`NOT_ESTABLISHED`** | ídem |
| ¿Varios PASID por proceso? | **`NOT_ESTABLISHED`** | ídem |
| ¿Cómo se recupera `fpriv` desde un PASID? | **`NOT_ESTABLISHED`** | ídem |
| Cuándo se elimina la asociación | **`NOT_ESTABLISHED`** | ídem |
| ¿Puede atribuir un FD? | **`NOT_ESTABLISHED`** | no hay puente leído |
| ¿Es obligatorio para atribución? | **NO**, y la documentación apunta a lo contrario | V2/S4 |

**No se asume `PASID = PID`, ni `PASID = drm_file`, ni `PASID = client_id`.** Ninguna de esas
igualdades fue encontrada, y dos están desmentidas por el código: `client_id` es un contador por boot
independiente del proceso, y `drm_file.pid` es un `struct pid` reasignable.

---

## 8 · GEM_ANALYSIS

**RELATION**: `drm_file → object_idr → GEM objects`
`SOURCE`: K2 `drm_gem_open()`: `idr_init_base(&file_private->object_idr, 1);`
`ASSIGNED`: K2 `drm_gem_handle_create_tail()`: `idr_alloc(&file_priv->object_idr, …)` y
`idr_replace(&file_priv->object_idr, obj, handle)`
`CONSUMED`: K1 `drm_show_memory_stats()`: `idr_for_each_entry(&file->object_idr, obj, id)`
`DIRECT`; `IDENTITY UNIT`: handles GEM por `drm_file`

**RELATION**: `GEM object → múltiples drm_file` — **DIRECT, y es la clave de F-02**
`SOURCE`: K2 `drm_gem_open_ioctl()` llama `drm_gem_handle_create_tail(file_priv, obj, &handle)`
con un **`file_priv` distinto** del que creó el objeto (importación por dma-buf o flink). La
asignación es `drm_vma_node_allow(&obj->vma_node, file_priv)`.
`INTERPRETATION`: **un mismo `drm_gem_object` puede estar en el `object_idr` de varios `drm_file`.**
`LIMITATION`: la importación es por dma-buf/flink; no implica copia
`FALSIFIER`: que `object_idr` fuera global y no por `drm_file`
`CLASSIFICATION`: **`ESTABLISHED`** — la relación es **muchos-a-muchos**

**RELATION**: `GEM → shared/private` — **DIRECT**
`SOURCE`: K1 `drm_show_memory_stats()`: `if (drm_gem_object_is_shared_for_memory_stats(obj))
status.shared += obj->size; else status.private += obj->size;`
`INTERPRETATION`: **"memoria de un cliente" es un conceito derivado**, no una propiedad del objeto.
`CLASSIFICATION`: **`ESTABLISHED`**

**RELATION**: `GEM object → struct file` (propio, shmem)
`SOURCE`: K2 `drm_gem_object_init()`: `obj->filp = filp;` (shmem), distinto del `struct file` del DRM
`CLASSIFICATION`: **`ESTABLISHED`** — y relevante: el `struct file` de un GEM **no** es el del FD DRM

**Lo que un GEM object NO tiene** (relevante para la pregunta del encargo): en el código leído no
aparece ningún campo `pid`, `fpriv`, `vm`, `pasid` ni `client_id` dentro de `drm_gem_object`. La
atribución de memoria es **por `drm_file`**, no por objeto.

## 9 · CLIENT_ID_ANALYSIS

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| Dónde se genera | `drm_file_alloc()`, `atomic64_inc_return(&ident)` | K1 |
| Dónde se almacena | `drm_file.client_id` (`u64`) | K1 |
| ¿Pertenece a `drm_file`? | **Sí**, y solo a él | K1 |
| ¿AMDGPU lo consulta? | **`NOT_ESTABLISHED`** | fuente inaccesible |
| ¿AMDGPU mantiene índice `client_id`→`fpriv`? | **`NOT_ESTABLISHED`** | ídem |
| ¿Se puede reconstruir por otra relación? | **No por `pid`** (contador global, sin relación con el proceso) | K1 |

`CLASSIFICATION`: **`ESTABLISHED`** para origen/almacenamiento; **`NOT_ESTABLISHED`** para cualquier
uso en amdgpu.

---

## 10 · RELATIONSHIP_CHAIN

### CASO OBSERVADO — mitad DRM (fuente primaria)

```
drm_file
 ├─ client_id   = atomic64_inc_return(&ident)   [global, por boot]   DIRECT
 ├─ pid         = get_pid(task_tgid(current))   [TGID, REASIGNABLE]   DIRECT
 ├─ minor       -> drm_device -> PCI                                DIRECT
 ├─ filp        <-> struct file  (filp->private_data <-> priv->filp)  DIRECT
 ├─ lhead       -> dev.filelist                                     DIRECT
 ├─ object_idr  -> GEM objects   (muchos-a-muchos)                  DIRECT
 └─ driver_priv -> [???]      <-- UNICO LINK NO VERIFICADO
```

### CASO A — `drm_file → fpriv → VM → PASID → task_info`
**NO DETERMINADO.** Requiere K3/K4. `NOT_AVAILABLE`.

### CASO B — `drm_file → fpriv → VM → PASID`, sin `task_info`
**NO DETERMINADO.** `NOT_AVAILABLE`.

### CASO C — `drm_file` y `fpriv` solo comparten PID
**NO DETERMINADO**, y **no sería acceptable** como identidad: el `client_id` es un contador global
sin relación con el proceso, así que un PID compartido no identifica un objeto. Si resultara ser
así, sería `INFERENCE_ONLY`.

### CASO D — no existe puente
**NO DETERMINADO.** No se puede afirmar `BRIDGE_NOT_ESTABLISHED` por ausencia de lectura.

---

## 11 · DUPLICATION_CASES

| Caso | Qué hace el código | Clase |
|---|---|---|
| 2 FDs → mismo `drm_file` (`dup`, `fork`) | `client_id` **igual**: se asigna en `drm_file_alloc`, no por FD | `ESTABLISHED` |
| 2 `drm_file` → mismo PID | `pid` **igual** (mismo `task_tgid`); `client_id` **distinto** (contador) | `ESTABLISHED` |
| 1 proceso → múltiples VM | `NOT_ESTABLISHED` | falta K4 |
| 1 proceso → múltiples PASID | `NOT_ESTABLISHED` | falta K4 |
| GEM_object compartido/importado | **varios `drm_file` en un `object_idr`**; el core lo marca `shared` | `ESTABLISHED` |
| GEM_object reasignado de proceso | `drm_file_update_pid()` re-apunta el `drm_file` completo | `ESTABLISHED` |

**El caso decisivo para F-02**: `dup()` produce dos FDs con **un** `client-id`. El proyecto tiene
evidencia de host de **9 FDs y 3 ids en un proceso**, consistente con esto.

## 12 · LIFETIME_ANALYSIS

| Objeto | Creado | Liberado |
|---|---|---|
| `drm_file` | `drm_open()` → `drm_open_helper()` → `drm_file_alloc()` | `drm_release()` → `drm_close_helper()` → `drm_file_free()`; `put_pid(file->pid)` |
| `client_id` | en `drm_file_alloc()` | muere con el `drm_file`; el contador persiste hasta el boot |
| `object_idr` | `drm_gem_open()` (`idr_init_base`) | `drm_gem_release()` (`idr_destroy`) |
| GEM ref | `drm_gem_handle_create_tail()` | `drm_gem_handle_delete()` / `drm_gem_release()` |

**Ventana**: todo es coherente dentro de una misma lectura de `/proc`. **Entre dos lecturas**,
`client_id` puede haber sido reasignado por el reinicio del contador (solo tras reboot) y el `pid`
de un `drm_file` superviviente puede haber cambiado.

## 13 · CONFLICTS

| ID | Conflicto | Estado |
|---|---|---|
| **B-1** | `drm-usage-stats` (V1) llama a `drm-client-id` *"A unique id **for fdinfo**"*; el código lo confirma literalmente, pero la spec también lo describe comoel criterio para distinguir FDs duplicados/compartidos | **RESOLVED**: es un id de cliente, y el "fdinfo" es su **superficie**, no su propósito |
| **B-2** | `client_id` es global-por-boot en el código, mientras la spec ofrece "global **or** per-device" | **RESOLVED**: la implementación cumple el caso más fuerte |
| **B-3** | V2: Y `client ID` de un page fault = GPU block; `drm-client-id` = cliente DRM | **`CONFLICT` NO RESUELTO** (sin cambios) |
| **B-4** | **`drm_file.pid` mutable** vs la lectura de V1/V2 de que `pid` es *"Process that is using this file"* | **NO ES CONFLICTO**: el doc dice "using", y el código re-apunta al que lo usa. Se **refuerza** la lectura de V2 |
| **B-5** | `drm-pdev` marcado `optional` en la spec vs emitido incondicionalmente en PCI | **RESOLVED**: `optional` significa "el driver puede no emitirlo"; el core lo emite **si y solo si** el bus es PCI |

## 14 · NEGATIVE_RESULTS

`drm_pdev` fuera del `if (dev_is_pci())` · `client_id` derivado de PID · `client_id` derivado de
minor · `drm_file` con campo `vm`/`pasid`/`fpriv` en el core · `drm_gem_object` con `pid`/`fpriv`/
`pasid`/`client_id` en el código leído · **`amdgpu_fpriv`, `amdgpu_vm`, `task_info`,
`amdgpu_pasid_get_fpriv_locked`, `amdgpu_vm_get_task_info_pasid`, `amdgpu_vm_set_task_info`:
0 archivos leídos**.

## 15 · UNKNOWN

Cuándo y quién invoca `drm_file_update_pid()` · si amdgpu re-usa `client_id` · si amdgpu indexa por
`client_id` · la definición real de `driver_priv` para amdgpu · toda la cadena PASID.

## 16 · NOT_ESTABLISHED

`driver_priv → amdgpu_fpriv` · `fpriv → VM` · `VM → PASID` · `PASID → task_info → PID` ·
`PASID ↔ drm_file` · cualquier uso de `client_id` dentro de amdgpu.

## 17 · FALSIFIERS

| Afirmación | Falsificador |
|---|---|
| `client_id` es global por boot | que el contador fuera por-`minor` o por-`drm_device` |
| `drm_file.pid` es reasignable | que `drm_file_update_pid` no existiera o fuera `#if 0` |
| `drm-pdev` solo en PCI | que se emitiera también en buses no-PCI |
| GEM muchos-a-`drm_file` | que `object_idr` fuera global |
| `driver_priv` es el hook del driver | que `dev->driver->open` no lo usara |
| **No hay puente a PASID** | **`amdgpu_drv.h` mostró un campo que lo enlace directamente** |

## 18 · IMPACT_ON_F01

**No resuelve F-01.** F-01 preguntaba si `any()` o `all()` es correcto. Esta investigación muestra
que los tres campos **viven en relaciones distintas**, y que **`pasid` pertenece a una cuarta** que
no se pudo verificar. La disposición de `client_id` refuerza que **no es una clave de proceso** y por
tanto no puede servir por sí sola para "atribuir a proceso".

`F-01` sigue **`REQUIREMENT_UNRESOLVED`**, y ahora con un dato nuevo: **`drm-client-id` es global y
por-boot**, lo que lo hace unsuitable as a *process* key pero adecuado como *client* key.

## 19 · IMPACT_ON_F02

**Refuerza F-02 con código primario.** `client_id` se asigna **una vez por `drm_file`**, y
`drm_file` se asigna **una vez por `open()`**. Por tanto **`#client-ids ≤ #FDs`, con desigualdad
estricta cuando hay `dup()`, `fork()` o FDs compartidos**. Contar FDs como clientes DRM es
**incorrecto por construcción del kernel**, no por convención del proyecto.

## 20 · IMPACT_ON_PASID_ATTRIBUTION

`PASID` sigue **`NOT_ESTABLISHED`** en cuanto a relación con `drm_file`. Lo que sí se hace es
**descartar dos igualdades falsas** con evidencia de código: `PASID ≠ client_id` (este es un contador
global, no un identificador de espacio de direcciones) y `PASID ≠ pid` (este es un `struct pid`
reasignable). Ninguna de las dos era una hipótesis nuestra, pero ahora ambas tienen base de
refutación.

## 21 · FINAL_CLASSIFICATION

### `SOURCE_INCOMPLETE`

No es `BRIDGE_ESTABLISHED`: **no se leyó** `amdgpu_drv.h` ni `amdgpu_vm.c`, que son donde el puente
estaría. Afirmarlo sin haberlos leído sería inventar.

No es `BRIDGE_NOT_ESTABLISHED`: el puente **no fue buscado en el lugar donde está**; afirmar que no
existe sería convertir una limitación de acceso en evidencia de ausencia — precisamente lo que
`AGENTS.md` prohíbe.

Es `SOURCE_INCOMPLETE` porque: (i) la mitad DRM está **verificada con fuente primaria** y produce
cinco relaciones `ESTABLISHED`; (ii) la mitad AMDGPU es **`NOT_AVAILABLE`** por un bloqueo de acceso
reproducible y caracterizado; (iii) el único eslabón no verificado de toda la cadena es
`driver_priv → amdgpu_fpriv`, y los tres siguientes dependen de él.

## 22 · NEXT_STEP

**Una sola acción**: obtener `drivers/gpu/drm/amdgpu/amdgpu_drv.h` y `amdgpu_vm.c` por una vía **no**
HTTP-de-CDN — el paquete Debian/Ubuntu `linux-source-$(uname -r)` o un `linux-source` de
`archive.ubuntu.com`, que es un `.tar.xz` descargable y no un endpoint de API — y verificar **tres
campos exactos**: (1) si `struct amdgpu_fpriv` contiene un `vm` y un `pasid`; (2) si
`amdgpu_vm` contiene `task_info` con PID/TGID; (3) **dónde se asigna `file->driver_priv`**.

Si (3) aparece en `drm_open`/`amdgpu_open` con `kzalloc(sizeof(struct amdgpu_fpriv))`, el Caso A
queda establecido en su mitad observable. Si (1) o (2) fallan, el Caso D queda demostrado **con
fuente**, no por falta de acceso — que es la diferencia entre `BRIDGE_NOT_ESTABLISHED` y
`SOURCE_INCOMPLETE`.
