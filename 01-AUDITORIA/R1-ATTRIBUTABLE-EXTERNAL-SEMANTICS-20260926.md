# R1-ATTRIBUTABLE-EXTERNAL-SEMANTICS-20260926

`DOCUMENT_KIND = RESEARCH`
`NORMATIVE_STATUS = RESEARCH_ONLY` — no es requisito, no es propuesta de requisito, no está
adoptado. No sustituye ni modifica `AGENTS.md`,
`R1-ATTRIBUTABLE-NODE-ROWS-REQUIREMENT-20260926.md` ni
`R1-ATTRIBUTABLE-DEFINITION-RESEARCH-20260926.md`.
`CODE_CHANGED = NO` · `COLLECTOR_CHANGED = NO` · `TESTS_CHANGED = NO` · `AGENTS.md = UNCHANGED`
`HOST_MEASUREMENT = NONE` · `COMMIT = NO`

> **`ATRIBUIBLE` no se cierra en este documento.** Clasificación final: `PARTIALLY_DEFINED`.
> Ver §8.

---

## 1 · COBERTURA DE BÚSQUEDA EXTERNA

| Fuente | Resultado |
|---|---|
| Kernel `Documentation/gpu/drm-internals` (7.3.0-rc4, 3074 líneas) | **OBTENIDA** |
| Kernel `Documentation/gpu/drm-usage-stats` (7.3.0-rc4) | **OBTENIDA** (ronda anterior) |
| Kernel `Documentation/gpu/drm-uapi` (7.3.0-rc4, 3630 líneas) | **OBTENIDA** (ronda anterior) |
| `man5 proc_pid_fd` / `proc_pid_fdinfo` (man-pages 6.19) | **OBTENIDAS** (ronda anterior) |
| `git.kernel.org` cgit — fuente amdgpu | **INACCESIBLE** (Anubis) |
| `elixir.bootlin.com` — fuente amdgpu | **INACCESIBLE** (Anubis) |
| `docs.kernel.org/gpu/amdgpu/thermal` | **OBTENIDA** pero irrelevante: es PM/thermal, no fdinfo |
| `docs.kernel.org/admin-guide/dmem.html` | **404** |
| Búsquedas web (4 intentos: semántica de `pasid`, `pasid` amdgpu, atribución en nvtop, dmem cgroup) | **0 resultados** |
| URLs adivinadas (`raw.githubusercontent.com/…`) | **404** |

**Limitación honesta de esta ronda**: la herramienta de búsqueda web no devolvió ningún resultado
en ninguno de los 4 intentos, y las fuentes de código de amdgpu siguen inaccesibles. Por eso las
secciones de herramientas de monitoreo GPU y de amdgpu/PASID quedan con cobertura **parcial**, y
así se declaran.

---

## 2 · HALLAZGO PRINCIPAL: LA CADENA FORMAL EXISTE Y ESTÁ DOCUMENTADA

`drm-internals` documenta `struct drm_file` campo por campo. Los cuatro campos que sostienen la
cadena tienen descripción textual del kernel:

| Campo | Descripción literal del kernel |
|---|---|
| `pid` | **"Process that is using this file."** |
| `client_id` | **"A unique id for fdinfo"** |
| `minor` | **"struct drm_minor for this file."** |
| `filp` | **"Pointer to the core file structure."** |
| `master` | "Master this node is currently associated with… **Only relevant if `drm_is_primary_client()` returns true.**" |
| `debugfs_client` | "debugfs directory for **each client** under a drm node." |
| `lhead` | "List of all open files of a DRM device, linked into `drm_device.filelist`." |

`struct drm_file`, descripción: **"This structure tracks DRM state per open file descriptor."**

De `struct drm_device`:

| Campo | Descripción literal |
|---|---|
| `filelist` | **"List of userspace clients**, linked through `drm_file.lhead`." |
| `clientlist` | "List of **in-kernel clients**." |
| `primary` / `render` / `accel` | "Primary node." / "Render node." / "Compute Acceleration node" |
| `dev` | "Device structure of bus-device" |
| `open_count` | "Usage counter for outstanding files open" |

Y las funciones:

- `drm_is_primary_client()` — *"Returns true if this is an open file of the primary node, i.e.
  **`drm_file.minor` of `file_priv` is a primary minor**."*
- `drm_is_render_client()` — *"…i.e. **`drm_file.minor` of `file_priv` is a render minor**."*

Y `drm_driver.show_fdinfo` — *"Print device specific fdinfo. **See DRM client usage stats**."*

### 2.1 Cadena reconstruible

```
                    drm_file.pid
   PROCESS  <─────────────────────┐   ("Process that is using this file")
      |                           |
      | 1 proceso : N FDs         v
      |                    struct drm_file   ("tracks DRM state per open file descriptor")
      |                           |
      |                           +--filp--> struct file --> Linux FD
      |                           |
      |                           +--client_id--> "a unique id for fdinfo"
      |                           |
      |                           +--minor-----> drm_minor (primary | render | accel)
      |                           |                     |
      |                           |                     v
      |                           |               drm_device  ("dev" = struct device)
      |                           |                     |
      |                           |                     v
      |                           |               PCI device / BDF
      |                           |
      |                           +--master----> drm_master   (solo si drm_is_primary_client)
      |                           |
      |                           +--debugfs_client--> "debugfs directory for each client"
      |                           |
      +-- N : M con los clients--+
```

Los cinco enlaces son **miembros de struct documentados**. Esto es una `DERIVED_DEFINITION`
construida sobre `DIRECT_DEFINITION` de cada campo. **No** es una cita literal de una definición de
"attribution", porque el kernel **no define "attribution"** (§3).

---

## 3 · EVIDENCIA NEGATIVA, REFORZADA

| Término | `drm-internals` (3074 l.) | `drm-uapi` (3630 l.) | `drm-usage-stats` |
|---|---|---|---|
| `attribut*` | **0** | 1 — *"Common trace events attributes"* (no pertinente) | 0 |
| `pasid` | **0** | **0** | **ausente** |
| `ownership` | 0 | 0 | 0 |
| `owns` / `owned` | 0 | 3 — sobre `drm_master` y *display resource leasing* | 0 |

**Tres documentos del kernel, 6704+ líneas: el término "attribution" no aparece con sentido
relevante, y `pasid` no aparece en absoluto.**

### 3.1 El kernel sí tiene un concepto de *ownership*, y es otro

De `drm-uapi`: *"The original DRM master of a device **'owns'** the available drm resources"*, con
`owner` / `lessor` / `lessee` de `drm_master` en el contexto de **display resource leasing**.

Es decir: el vocabulario de *ownership* del kernel existe, es preciso, y se aplica a
**`drm_master` y recursos de display** — **no** a FDs, ni a clients, ni a procesos. Importarlo para
nuestro caso sería un error de vocabulario, no una definición.

---

## 4 · HALLAZGO QUE REFUERZA F-02

`drm-usage-stats` (ronda anterior) established: `drm-client-id` es *"Unique value relating to the
open DRM file descriptor used to **distinguish duplicated and shared** file descriptors.
Conceptually the value **should map 1:1 to the in kernel representation of `struct drm_file`"*.

`drm-internals` (esta ronda) establece: `struct drm_file` *"tracks DRM state **per open file
descriptor**"*.

**Composición de dos `DIRECT_DEFINITION` del kernel:**

```
drm-client-id  <->  1:1  <->  struct drm_file  <->  1:1  <->  open file descriptor
```

Consecuencia directa: **un `drm-client-id` NO es un FD**. Varios FDs pueden compartir un
`drm_file` (dup, fork, `SCM_RIGHTS`) y por tanto compartir un `drm-client-id`. La cuenta de FDs
excede a la de clients exactamente en esos casos.

Esto **ancla F-02 en fuente primaria del kernel**, y no solo en la inferencia de la ronda anterior.
El conteo del collector (`card_clients` = FDs) sobrecuenta clients DRM por construcción siempre que
haya FDs duplicadas o compartidas, y el proyecto tiene evidencia de host de 1 proceso con 9 FDs y
3 ids.

---

## 5 · `client_id`: LA RESTRICCIÓN SEMÁNTICA MÁS IMPORTANTE

El kernel define su propio campo así:

> `client_id` — **"A unique id for fdinfo"**

Es decir: **el propósito documentado de `client_id` es la identificación en fdinfo**, no la
atribución a proceso, ni la atribución a recurso, ni la identidad de dispositivo.

Consecuencias:

1. `drm-client-id` **no** está documentado como instrumento de atribución a proceso. El proceso se
   obtiene por `drm_file.pid` y, en el collector, por el path `/proc/<pid>/fd/<n>`.
2. `drm-pdev` es la clave que documenta el **dispositivo** (S1: *"should contain the PCI slot
   address"*), y es `optional`.
3. Por lo tanto, la relación **proceso→cliente** en la terminología del kernel es `pid` + `client_id`
   como **dos hechos separados**, no como un identificador compuesto.

`PASID`: no aparece en ninguno de los tres documentos. `PASID_SEMANTICS = NOT_ESTABLISHED`, y esta
ronda **no mejora** esa clasificación: la amplify, porque la tercera fuente primaria tampoco lo
menciona.

---

## 6 · UNIDAD DE ATRIBUCIÓN: LO QUE LA EVIDENCIA ADMITE Y LO QUE NO

| Relación | ¿Documentada? | Fuente |
|---|---|---|
| `PROCESS → FD` | **Sí, DIRECT** | `drm_file.pid`; `proc_pid_fd(5)` |
| `FD ↔ DRM FILE` | **Sí, DIRECT** | `drm_file` "per open file descriptor"; `filp` |
| `DRM FILE → MINOR/NODE` | **Sí, DIRECT** | `drm_file.minor`; `drm_is_primary_client()` |
| `NODE → DEVICE` | **Sí, DIRECT** | `drm_device.dev` |
| `DEVICE → PCI/BDF` | **Sí, DIRECT** | `drm_device.dev` = "Device structure of bus-device" |
| `FD → DRM CLIENT` | **Sí, DERIVED** | `client_id` ↔ `drm_file` 1:1 (S1) + `drm_file` per-FD (S9) |
| `DRM FILE → MASTER` | **Sí, DIRECT**, pero **condicional** | `drm_file.master`, "Only relevant if `drm_is_primary_client()`" |
| `CLIENT → RESOURCE` | **No** | la memoria es *por cliente* (S1: `drm-total-<region>`), pero la relación recurso→client no está normada |
| `RESOURCE → PROCESS` | **No directamente** | sería composición de las anteriores = `INFERENCE` |
| `PASID → {process, address space, VM}` | **`NOT_ESTABLISHED`** | 0 ocurrencias en 6704+ líneas |

**Y la relación que el requisito humano sí nombra, `AGENTS.md:32`** ("Identify a device by PCI
identity, never by its `cardN` name"), es exactamente la cadena `minor → drm_device → dev → BDF`,
que el kernel documenta de punta a punta.

---

## 7 · DEFINICIONES EXTERNAS ENCONTRADAS

Ninguna es una definición del término "attribution". Todas son `DERIVED_DEFINITION` o
`DIRECT_DEFINITION` de una relación.

| ID | Definición | `DIRECTNESS` | Fuente | Autoridad |
|---|---|---|---|---|
| X-1 | Un FD pertenece a un proceso | **DIRECT** | `drm_file.pid` | `EXTERNAL_SPEC` |
| X-2 | Un FD es un cliente DRM | **DIRECT** | `drm_file` "per open file descriptor"; `drm_device.filelist` = "List of userspace clients" | `EXTERNAL_SPEC` |
| X-3 | Dos FDs son el mismo cliente si comparten `drm-client-id` | **DIRECT** | S1: "map 1:1 to `struct drm_file`" + "distinguish duplicated and shared" | `EXTERNAL_SPEC` |
| X-4 | Un cliente pertenece a un nodo | **DIRECT** | `drm_file.minor`; `drm_is_primary_client()` | `EXTERNAL_SPEC` |
| X-5 | Un nodo pertenece a un dispositivo PCI | **DIRECT** | `drm_device.dev`; `drm_minor` | `EXTERNAL_SPEC` |
| X-6 | Un cliente tiene una dirección de memoria | **DIRECT** | S1: `drm-total-<region>`, `drm-resident-<region>`, `drm-shared-<region>` | `EXTERNAL_SPEC` |
| X-7 | Una dirección de memoria se vuelca por debugfs, no por fdinfo | **DIRECT** | S2: `drm_debugfs_gpuva_info()`, `drm_gpuvm` | `EXTERNAL_SPEC` |
| X-8 | Un maestro posee recursos de display | **DIRECT**, y es **otro concepto** | S2: leasing, `drm_master` | `EXTERNAL_SPEC` |
| X-9 | Un recurso se contabiliza a un **contenedor** | **NO** | `drmm_cgroup_register_region()` aparece en S9 como función; su documentación no se obtuvo (404) | `NOT_ESTABLISHED` |

**X-9 es importante por lo que no pudo obtenerse**: `drm-internals` menciona
`drmm_cgroup_register_region()` — *"Register a region of a DRM device to cgroups"*. Es un mecanismo
de **atribución de recurso a cgroup**, es decir a una **cuarta unidad** (contenedor), distinta de
proceso, client y FD. La documentación del controlador no se pudo obtener. Se registra como
`NOT_ESTABLISHED` y como **hueco de cobertura**, no como ausencia.

---

## 8 · CLASIFICACIÓN FINAL

### `PARTIALLY_DEFINED`

Qué la evidencia establece, con fuente primaria:

1. La cadena `PROCESS → FD → DRM FILE → MINOR/NODE → DEVICE → PCI` está **documentada campo por
   campo** por el kernel. Es la `DERIVED_DEFINITION` más sólida disponible.
2. "Cliente DRM" tiene **tres** definiciones distintas en la documentación del kernel, y no
   concuerdan: (a) `drm_file` ("per open file descriptor"); (b) lo que `drm-client-id` identifica
   (1:1 con `drm_file`); (c) un "grupo de clients" (`drm_master`). Con render nodes, (c) **no
   existe**.
3. `client_id` tiene un propósito documentado y acotado: *"a unique id for fdinfo"*.
4. `ownership` en el kernel es un concepto **distinto**, sobre `drm_master`.
5. `pasid` no aparece en 6704+ líneas de documentación DRM del kernel.

Qué **no** se establece:

1. **No existe una definición de "attribution"/"atribuible"** en la documentación DRM del kernel.
2. `PASID` sigue `NOT_ESTABLISHED`.
3. `CLIENT → RESOURCE → PROCESS` es `INFERENCE`, no fuente.
4. La atribución a **contenedor/cgroup** es un cuarto eje potencial pero **no documentado** en esta ronda.
5. No se obtuvo **ninguna** fuente de herramientas de monitoreo GPU (búsquedas vacías), que es
   donde el término "attribution" podría tener un uso empírico establecido.

Por eso **no** es `DEFINED` (las relaciones están, la definición del término no) y **no** es
`AMBIGUOUS` en el mismo sentido que antes: la parte de relaciones pasó de ambigua a
documentada, y lo que queda ambiguo es **la selección** de qué relaciones debe exigir la fila.

---

## 9 · LO QUE ESTA RONDA CAMBIÓ RESPECTO DE LA ANTERIOR

| Antes | Ahora | Fuente |
|---|---|---|
| "¿El kernel permite construir la cadena PROCESS→DRM FILE→CLIENT→DEVICE?" `UNKNOWN` | **Sí, y la documenta campo por campo** | `drm-internals` S9 |
| F-02 apoyado en inferencia + spec | **F-02 anclado en `DIRECT_DEFINITION` del kernel** | S9 + S1 |
| "`drm-client-id` sirve para atribuir" | **Su propósito documentado es fdinfo; no proceso** | S9: `client_id` = "A unique id for fdinfo" |
| `ownership` sin_definition | El kernel **sí** lo define, y es **otro concepto** | S2: `drm_master` leasing |
| Cuarta unidad de atribución (cgroup) no considerada | **Identificada y no documentada** | S9: `drmm_cgroup_register_region()` |

Sin cambios: `PASID_SEMANTICS = NOT_ESTABLISHED`; `drm-pdev` y `drm-client-id` siguen `optional` en
la spec; no hay definición del término "attribution" en el kernel.
