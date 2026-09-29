# R1-TECHNICAL-SEMANTIC-MODEL-20260926

`DOCUMENT_KIND = SEMANTIC_RECONSTRUCTION` · `NORMATIVE_STATUS = RESEARCH_ONLY`
Reconstrucción **independiente del requisito del proyecto**. Ninguna entidad ni propiedad de este
documento se define a partir de `AGENTS.md`, del plan, del collector o de sus tests.
`CODE_CHANGE_ALLOWED = NO` · nada implementado ni modificado.

**Regla central aplicada**: kernel → observabilidad → requisito. En ese orden, y no al revés.

**Universo de fuentes** (todas obtenidas y leídas en esta ronda, `linux` v6.12):
`drivers/gpu/drm/drm_file.c` (996 L) · `include/drm/drm_file.h` · `drivers/gpu/drm/drm_internal.h` ·
`include/drm/drm_drv.h` (554 L) · `include/drm/drm_gem.h` · `drivers/gpu/drm/drm_gem.c` (1535 L) ·
`Documentation/gpu/drm-usage-stats.rst` (189 L).
`drivers/gpu/drm/amdgpu/` → **404 confirmado también por la API de contenidos** → `SOURCE_INCOMPLETE`.

`TEMPORALITY` = linux v6.12 mainline, descargado en esta sesión · `HOST_SCOPE` = ninguno.

---

# FASE 1 · UNIVERSO DE ENTIDADES

Tabla exclusivamente semántica. "client" **nunca** se usa como entidad genérica; donde aparece se
dice qué objeto es.

| # | `ENTITY` | `UNIT` | `IDENTITY` | `RELATIONS` | `SOURCE` | `STATE` |
|---|---|---|---|---|---|---|
| 1 | `drm_device` | un driver+dispositivo | `struct device *dev` embebido; `dev->kdev` | minor, filelist, driver, `dev` | `drm_drv.h`; uso `file->minor->dev` (`drm_file.c:230`) | `ESTABLISHED` |
| 2 | `drm_minor` | un nodo `/dev/dri/N` | `index` (**número de minor**) + `type` | `kdev` (device Linux del nodo) → `dev` (drm_device padre) | `drm_file.h:77-87` | `ESTABLISHED` |
| 3 | `drm_file` | **una apertura DRM** | sin identidad propia comparable; tiene `magic`, `client_id` | minor, pid, filp, driver_priv, object_idr, master | `drm_file.h` (`struct drm_file`) | `ESTABLISHED` |
| 4 | `struct file` / `filp` | un descriptor abierto en el kernel | puntero inode/inode; **no** tiene identidad DRM | `private_data` ↔ `drm_file` | `drm_file.c` (`f->private_data`) | `ESTABLISHED` |
| 5 | `drm-client-id` | un `u64` | contador `atomic64_inc_return(&ident)` **estático de módulo**; **1:1 con `drm_file` por construcción** | — | `drm_file.c:142`; spec `drm-usage-stats.rst:64-72` | `ESTABLISHED` (implementación) · `CONFLICT_UNRESOLVED` (alcance de unicidad, ver N-1) |
| 6 | `drm-pdev` | un string `aaaa:bb.cc.d` | **slot address PCI** — `domain:bus:slot.func`; **sin vendor/device** | derivado de `file->minor->dev->dev` | `drm_file.c` (`drm_show_fdinfo`) | `ESTABLISHED` |
| 7 | PID de `drm_file` | `struct pid *` | `task_tgid(current)` en la apertura | reasignable por `drm_file_update_pid` | `drm_file.c:143`; `:drm_file_update_pid` | `ESTABLISHED` |
| 8 | PCI device | un dispositivo PCIe | BDF; `vendor`/`device`/`class` | `drm_device.dev` si `dev_is_pci` | `drm_drv.h`; rama `dev_is_pci` en `drm_file.c` | `ESTABLISHED` |
| 9 | GEM object / `object_idr` | un `drm_gem_object` por entrada del idr | id numérico **dentro del `drm_file`**; el objeto en sí es global | `drm_file.object_idr` | `drm_file.h` (`struct idr object_idr`); `drm_gem.c:884` | `ESTABLISHED` |
| 10 | `driver_priv` | `void *` opaco | **ninguna** en el core; lo define el driver | `drm_file.driver_priv` | `drm_file.h` | `ESTABLISHED` como existencia · `UNKNOWN` como semántica (opaco) |
| 11 | VM (GPU address space) | un espacio de direcciones GPU | según driver | PASID | solo AMDGPU docs | `SOURCE_INCOMPLETE` (estructura) |
| 12 | PASID | un **vmid** | vmid | proceso, **solo durante un page fault** | AMDGPU docs | `ESTABLISHED` (docs) · `SOURCE_INCOMPLETE` (puente a kernel) |
| 13 | proceso | un `task_struct` | PID/TGID del kernel | `drm_file.pid` | `drm_file.c:143` | `ESTABLISHED` |
| 14 | FD del proceso | una entrada de la tabla de descriptores | índice en la tabla de un proceso | abre → `struct file` | `proc_pid_fd(5)` | `ESTABLISHED` |

**Precisión de identidad (entidad 5 vs 6)**: `drm-client-id` y `drm-pdev` tienen **orígenes
distintos** en el kernel: el primero se asigna en `drm_file_alloc` (por `drm_file`); el segundo se
**deriva en el momento de imprimir**, desde `file->minor->dev->dev`. Por tanto **`drm-pdev` es
constante para todos los `drm_file` de un mismo dispositivo** y, por sí solo, **no discrimina
clientes**. `ESTABLISHED`.

---

# FASE 2 · RELACIONES

| # | `RELATION` | `EXTREMOS` | `DIRECCIÓN` | `UNIDAD` | `SOURCE` | `INMUTABILIDAD` | `STATE` |
|---|---|---|---|---|---|---|---|
| R1 | `FD → struct file` | entrada de tabla ↔ `struct file` | 1 descriptor → 1 file | descriptor | kernel VFS | inmutable por open | `ESTABLISHED` |
| R2 | `struct file → drm_file` | `f->private_data` | **1:1** | `struct file` | `drm_file.c` | inmutable | `ESTABLISHED` |
| R3 | `FD ↔ drm_file` | varios FDs : 1 `drm_file` | **N:1** | `drm_file` | spec: `drm-shared` *"shared with another file (e.g., have more than a single handle)"* | — | `ESTABLISHED` |
| R4 | `drm_file → client_id` | — | 1:1 | `drm_file` | `drm_file.c:142` | **inmutable** (asignado una vez) | `ESTABLISHED` |
| R5 | `drm_file → pid` | `rcu_replace_pointer` | 1:1 actual | `drm_file` | `drm_file.c:143` + `drm_file_update_pid` | **MUTABLE**, con excepción: `if (filp->was_master) return;` | `ESTABLISHED` |
| R6 | `drm_file → minor` | `file->minor` | **N:1** (1 minor por `drm_file`) | `drm_file` | `drm_file.c:144` | inmutable tras la apertura | `ESTABLISHED` |
| R7 | `minor → drm_device` | `minor->dev` | N:1 | minor | `drm_file.h:82` | inmutable | `ESTABLISHED` |
| R8 | `drm_device → PCI device` | `dev->dev` si `dev_is_pci` | 1:1 o 0:1 | `drm_device` | rama `dev_is_pci` | inmutable | `ESTABLISHED` |
| R9 | `drm_file → GEM objects` | `file->object_idr` | 1:N | `drm_file` | `drm_file.h`; `drm_gem.c:884` | **mutable** (altas y bajas) | `ESTABLISHED` |
| R10 | `drm_file → driver_priv` | puntero opaco | 1:1 | `drm_file` | `drm_file.h` | opaco | `ESTABLISHED` existencia · `UNKNOWN` semántica |
| R11 | `drm_file → drm_master` | `file->master` | 1:0:1 | `drm_file` | `drm_file.h` | — | `ESTABLISHED` que el campo existe |
| R12 | `VM → PASID` | — | 1:1 | vmid | AMDGPU docs | — | `SOURCE_INCOMPLETE` |
| R13 | `PASID → proceso` | — | 1:0:1 | — | AMDGPU docs: *"used to link a vmid to a system process id"* | **condicional**: *"If the process is active when the fault happens"* | `ESTABLISHED` que la relación es condicional y episódica |
| R14 | `drm_file → drm_file.pid → proceso` | — | N:1 | `drm_file` | R5 | mutable | `ESTABLISHED` |

### 2.1 Relaciones explícitamente **NO** asumidas

Ninguna de estas se afirma, y ninguna se usará:

`client_id = PID` · `client_id = proceso` · `client_id = FD` · `PASID = client_id` ·
`PASID = proceso` · `GEM object = proceso` · `engine = proceso` · `drm-pdev = identidad de cliente`.

`drm_file → GEM objects` **no** implica `GEM object → proceso`: el idr pertenece al `drm_file`, y el
`drm_file` tiene un pid (R5), pero esa cadena es una **inferencia composed**, no una relación
declarada por el core. `INFERRED`.

### 2.2 Hallazgos nuevos que corrigen conclusiones previas

- **N-1 · refuta mi afirmación de que `drm-pdev` es redundante.** La spec dice: *"Uniqueness of the
  value shall be either **globally unique, or unique within the scope of each device**, in which case
  `drm-pdev` shall be present as well."* (`drm-usage-stats.rst:70-72`). La **implementación actual**
  es global (`atomic64` estático), pero la **spec permite unicidad por dispositivo**, y en ese caso
  la identidad correcta es el **par `(drm-pdev, drm-client-id)`**. Mi afirmación previa ("`drm-pdev`
  redundante porque la identidad PCI ya está por sysfs") era **una generalización de la implementación
  a la spec, y es inválida como regla general**. `CONFLICT_UNRESOLVED` entre lo que el kernel hace
  hoy y lo que la spec permite.
- **N-2** `drm-pdev` se **deriva del dispositivo, no del `drm_file`**: es idéntico para todos los
  clientes de un mismo dispositivo. Sirve para **desambiguar** el `client-id` si la unicidad es por
  dispositivo; **no** identifica por sí mismo. `ESTABLISHED`.
- **N-3** `drm_file_update_pid` **exime** a quien fue master: `if (filp->was_master) return;`. El pid
  de un cliente master es el del **apertura original**, no el del usuario actual. Mi afirmación
  previa "el pid es reasignable" era correcta pero **incompleta**: la mutabilidad no es universal.
  `ESTABLISHED`.
- **N-4** La spec define `drm-shared-<region>` sobre **file**, no sobre cliente ni proceso
  (*"shared with another file (e.g., have more than a single handle)"*). Confirmación de R3 desde la
  spec, independiente de la implementación. `ESTABLISHED`.
- **N-5** `drm_print_memory_stats` (`drm_file.c`) **no** itera objetos: recibe un
  `drm_memory_stats` **pre-agregado** y lo formatea (`total = private + shared`). La iteración de
  `file->object_idr` ocurre en el **llamante** (`drm_gem.c:884`). Luego la estadística es un
  **agregado por `drm_file`**, no un inventario. `ESTABLISHED`.
- **N-6** El valor de `drm-pdev` es `domain:bus:slot.func` — **sin vendor ni device id**. La spec lo
  llama *"the PCI slot address"*. Por tanto `drm-pdev` **no basta** para probar identidad de
  dispositivo: hay que añadir vendor/device/class desde sysfs. `ESTABLISHED`.

---

# FASE 3 · PROPIEDADES

`SEMANTIC_STATUS` es semántico. **No se define PASS/FAIL del proyecto.**

### A · `NODE_COMPLETENESS`
`UNIT`: fd-table de un proceso · `DEFINITION`: la tabla pudo enumerarse y todo descriptor quedó
resuelto · `SOURCE`: `proc_pid_fd(5)` · `OBSERVATION_METHOD`: recorrer `/proc/<pid>/fd` y resolver
cada enlace · `POSITIVE_EVIDENCE`: cero symlinks sin resolver · `NEGATIVE_EVIDENCE`: un symlink no
resuelto · `UNKNOWN_CONDITION`: proceso no observable · `FALSIFIER`: que un fd sin resolver no
invalidara la completitud · `SEMANTIC_STATUS`: `ESTABLISHED`

### B · `NODE_PCI_IDENTITY`
`UNIT`: nodo (`drm_minor`) · `DEFINITION`: el minor pertenece al `drm_device` de la PCI objetivo ·
`SOURCE`: `minor->dev->dev`; R7+R8 · `OBSERVATION_METHOD`: sysfs, sin fdinfo · `POSITIVE_EVIDENCE`:
vendor+device+class+driver+BDF coinciden · `NEGATIVE_EVIDENCE`: no coinciden ·
`UNKNOWN_CONDITION`: sysfs ilegible · `FALSIFIER`: que el BDF no determinara el `drm_device` ·
`SEMANTIC_STATUS`: `ESTABLISHED`

### C · `DRM_FILE_IDENTITY`
`UNIT`: `drm_file` · `DEFINITION`: el par FD-abierto ↔ `drm_file` es 1:1 (R2) y varios FDs pueden
compartirlo (R3) · `SOURCE`: `f->private_data`; spec `drm-shared` · `OBSERVATION_METHOD`: **no hay
superficie directa**; se infiere por rutas de `/proc` y por `client_id` · `POSITIVE_EVIDENCE`: dos
lecturas con el mismo `client_id` → mismo `drm_file` · `NEGATIVE_EVIDENCE`: — ·
`UNKNOWN_CONDITION`: sin `client_id` no hay superficie observable · `FALSIFIER`: que un `client_id`
repetido correspondiera a `drm_file` distintos · `SEMANTIC_STATUS`: `INFERRED` (la 1:1 es del
kernel; la superficie de observación es del proyecto)

### D · `PROCESS_ASSOCIATION`
`UNIT`: par (`drm_file`, instante) · `DEFINITION`: qué proceso usa **actualmente** el `drm_file` ·
`SOURCE`: R5/R14; `drm_file.pid` · `OBSERVATION_METHOD`: **solo** la ruta `/proc/<pid>/fd/<n>`
(`drm_file.pid` no se expone en fdinfo) · `POSITIVE_EVIDENCE`: ruta legible bajo un pid ·
`NEGATIVE_EVIDENCE`: — · `UNKNOWN_CONDITION`:FD desaparecido a mitad · `FALSIFIER`: que la ruta no
identificara al proceso, o que el pid fuera inmutable · `SEMANTIC_STATUS`: `ESTABLISHED` con
reserva de temporalidad (R5 es mutable; master es excepción)

### E · `CLIENT_ID_PRESENCE`
`UNIT`: fdinfo de un FD · `DEFINITION`: la clave `drm-client-id` está presente en el texto ·
`SOURCE`: `drm_show_fdinfo` (impresión incondicional **si** el driver usa el helper) ·
`OBSERVATION_METHOD`: búsqueda de la clave en texto leído · `POSITIVE_EVIDENCE`: clave presente ·
`NEGATIVE_EVIDENCE`: clave ausente en texto legible y no vacío · `UNKNOWN_CONDITION`: texto no
leído · `FALSIFIER`: que el driver estándar pudiera omitirla · `SEMANTIC_STATUS`: `ESTABLISHED`

### F · `CLIENT_ID_DISCRIMINATION`
`UNIT`: `drm_file` · `DEFINITION`: usar los **valores** para separar y deduplicar `drm_file` ·
`SOURCE`: R4 + (`drm-pdev` si la unicidad es por dispositivo, N-1) · `OBSERVATION_METHOD`: extraer
el **valor** y construir el conjunto de pares distintos · `POSITIVE_EVIDENCE`: ≥1 valor distinto por
`drm_file` · `NEGATIVE_EVIDENCE`: — · `UNKNOWN_CONDITION`: sin valores, imposible ·
`FALSIFIER`: que dos `drm_file` distintos compartieran par `(pdev, client_id)` · `SEMANTIC_STATUS`:
`ESTABLISHED` que es posible; `ESTABLISHED` que el analizador actual **no** lo hace

### G · `MEMORY_CLIENT_STATS`
`UNIT`: agregado por `drm_file` · `DEFINITION`: bytes por región que consumen los buffer objects de
ese `drm_file` · `SOURCE`: `drm_print_memory_stats`; `drm-usage-stats.rst:143-160` ·
`OBSERVATION_METHOD`: claves `drm-memory-`/`drm-total-`/`drm-shared-`/`drm-resident-`/`drm-active-`
del texto · `POSITIVE_EVIDENCE`: valor por región · `NEGATIVE_EVIDENCE`: 0 (no descarta ausencia de
uso) · `UNKNOWN_CONDITION`: clave no exportada · `FALSIFIER`: que la spec definiera una clave de
memoria por proceso — no la define · `SEMANTIC_STATUS`: `ESTABLISHED` por `drm_file`;
`NOT_ESTABLISHED` hacia proceso

### H · `ENGINE_CLIENT_STATS`
`UNIT`: `drm_file` por engine · `DEFINITION`: tiempo que el engine estuvo **ocupado ejecutando
trabajos de ese cliente** · `SOURCE`: `drm-usage-stats.rst:79-92` · `OBSERVATION_METHOD`: claves
`drm-engine-<key>` · `POSITIVE_EVIDENCE`: `>0` ⇒ trabajo ejecutado belonging a ese `drm_file` ·
`NEGATIVE_EVIDENCE`: `=0` **no** implica no-uso — la spec exige *"stay with that larger previous
value"* ante retrocesos · `UNKNOWN_CONDITION`: clave ausente · `FALSIFIER`: que la clave fuera por
proceso, o que fuera monotónica · `SEMANTIC_STATUS`: `ESTABLISHED` por `drm_file`; acumulado y
**no monotónico**

### I · `VM_PASID_ASSOCIATION`
`UNIT`: vmid · `DEFINITION`: relación observable entre un espacio de direcciones GPU y un proceso ·
`SOURCE`: AMDGPU docs únicamente · `OBSERVATION_METHOD`: **ninguna disponible sin el puente** ·
`POSITIVE_EVIDENCE`: — · `NEGATIVE_EVIDENCE`: — · `UNKNOWN_CONDITION`: siempre, en esta fuente ·
`FALSIFIER`: que el puente exista en la fuente · `SEMANTIC_STATUS`: **`SOURCE_INCOMPLETE`**

### J · `CLIENT_PROCESS_ASSOCIATION`
`UNIT`: par (`drm_file`, proceso) · `DEFINITION`:Un `drm_file` identificado **y** su proceso actual
conocidos · `SOURCE`: compuesta de F y D · `OBSERVATION_METHOD`: ambas ·
`POSITIVE_EVIDENCE`: ambos términos · `NEGATIVE_EVIDENCE`: — · `UNKNOWN_CONDITION`: falta cualquiera ·
`FALSIFIER`: que F o D no fuera aplicable · `SEMANTIC_STATUS`: **`INFERRED`** — no hay ninguna
entidad ni relación en el kernel que la nombre

---

# FASE 4 · OBSERVABILIDAD

Cinco capas. **Nunca se colapsan.**

| Capa | Definición | No implica |
|---|---|---|
| `EXPOSED_BY_SYSTEM` | el kernel publica la atributo por alguna interfaz | que el analizador lo lea |
| `READABLE_BY_ANALYZER` | el analizador obtuvo la lectura sin error | que la lectura sea completa |
| `OBSERVED_IN_SAMPLE` | se obtuvo un valor en una ejecución concreta | que valgue para otro instante |
| `PROVES_PROPERTY` | el dato, por sí, demuestra la propiedad | que satisfaga el requisito |
| `SATISFIES_PROJECT_REQUIREMENT` | la propiedad cubre lo que el requisito pide | — |

### 4.1 `drm-client-id` ausente: cinco causas **distinguibles**

| Causa | Capa | Cómo se distingue |
|---|---|---|
| (a) clave opcional no exportada por el driver | `EXPOSED_BY_SYSTEM = FALSE` | el driver no llama a `drm_show_fdinfo` |
| (b) fdinfo no leído | `READABLE_BY_ANALYZER = FALSE` | error de lectura registrado |
| (c) fdinfo leído pero incompleto | `READABLE_BY_ANALYZER = PARTIAL` | texto truncado |
| (d) driver que no usa `drm_show_fdinfo()` | `EXPOSED_BY_SYSTEM = FALSE` | **mismo resultado observable que (a)** |
| (e) causa desconocida | `UNKNOWN` | ninguna de las anteriores verificable |

**`OBSERVED` — (a) y (d) son INDISTINGUIBLES desde el texto.** El texto solo muestra que
`drm-driver` no está. Eso es una cota de la observabilidad, no un dato del host.
**Ninguna de las cinco se convierte en `FAIL`.**

### 4.2 Capas por propiedad

| Propiedad | `EXPOSED_BY_SYSTEM` | `READABLE_BY_ANALYZER` | `OBSERVED_IN_SAMPLE` | `PROVES_PROPERTY` | `SATISFIES_PROJECT_REQUIREMENT` |
|---|---|---|---|---|---|
| A `NODE_COMPLETENESS` | sí | sí | sí | por sí sola | **determinado por G-1/G-2, pendiente** |
| B `NODE_PCI_IDENTITY` | sí (sysfs) | sí | sí | sí | pendiente |
| C `DRM_FILE_IDENTITY` | **no directamente** | no | — | solo vía F | pendiente |
| D `PROCESS_ASSOCIATION` | vía `/proc` | sí | sí | sí, **en el instante** | pendiente |
| E `CLIENT_ID_PRESENCE` | sí **si** el driver usa el helper | sí | sí | solo presencia | pendiente |
| F `CLIENT_ID_DISCRIMINATION` | sí | **no** (el analizador descarta valores) | — | sí, si se implementa | pendiente |
| G `MEMORY_CLIENT_STATS` | sí | sí (parcial) | no | por `drm_file` | pendiente |
| H `ENGINE_CLIENT_STATS` | sí | **no recolecta** | — | por `drm_file` | pendiente |
| I `VM_PASID_ASSOCIATION` | **desconocido** (`SOURCE_INCOMPLETE`) | no | no | — | pendiente |
| J `CLIENT_PROCESS_ASSOCIATION` | — | — | — | compuesta | pendiente |

---

# FASE 5 · PRESENCE ≠ VALUE ≠ DISCRIMINATION ≠ ATTRIBUTION

Cuatro capacidades. **Ninguna implica la siguiente.** Verificado contra el código del analizador.

| Nivel | Enunciado | Insumo | Estado en el analizador |
|---|---|---|---|
| `PRESENCE` | existe una clave `drm-client-id` | texto | **implementado** (`:2783`) |
| `VALUE` | tenemos el número | texto + parseo | **no implementado** — la función de atribución está escrita *"Presence only, never a value"* (`:1041-1051`) |
| `DISCRIMINATION` | los valores permiten separar `drm_file` | valores + conjunto | **no implementado** — requiere además `drm-pdev` si la unicidad es por dispositivo (N-1) |
| `ATTRIBUTION` | podemos establecer una relación con **otra entidad** | … + la definición de esa entidad | **no definido**: la entidad de destino nunca se nombra |

**Consecuencia**: una implementación que solo llega a `PRESENCE` **no puede** sostener `DISCRIMINATION`
ni `ATTRIBUTION`. El salto no es de esfuerzo, es de información.

---

# FASE 6 · ESTADOS DE VACÍO Y ATRIBUTO

| Estado | Definición formal | **NO** permite concluir |
|---|---|---|
| `EMPTY_UNIVERSE` | `∀x ∈ F(nodo) : P(x)` donde `F(nodo) = ∅` | que `P` se cumpla; la verdad vacua informa del **universo**, no de la propiedad |
| `NO_DRM_FD` | el barrido no encontró ningún FD DRM | que no haya clientes DRM en el sistema; solo en el barrido |
| `NO_OBSERVATION` | la lectura no se intentó o su alcance no cubre el objeto | nada del objeto |
| `READ_ERROR` | se intentó y falló | que el atributo esté ausente — **es evidencia incompleta**, no ausencia |
| `ATTRIBUTE_ABSENT` | se leyó el texto y la clave **no** está | que el driver sea inválido; que P no se cumpla |
| `ATTRIBUTE_PRESENT` | la clave está | nada más: ni su valor, ni unicidad, ni discrimina |
| `ATTRIBUTE_INSUFFICIENT` | la clave está pero no alcanza para la propiedad | que la propiedad se cumpla |
| `UNKNOWN` | no se pudo determinar | nada |

**Regla**: `∀x∈∅ P(x)` **no** es evidencia positiva de `P`. `ESTABLISHED` como regla lógica;
su transgresión es el vicio que este modelo impide.

`EMPTY_UNIVERSE` ≠ `NO_DRM_FD`: el primero es sobre **el nodo**, el segundo sobre **el barrido**.
Un proceso con FDs solo en `card1` tiene `EMPTY_UNIVERSE` en render y **no** `NO_DRM_FD`.

---

# FASE 7 · MODELO DEL PROYECTO (después de las fases 1-6)

Mapeo **post-hoc** desde el modelo técnico hacia los artefactos del proyecto. Ninguna columna
deriva su semántica del nombre.

| Artefacto | Qué mide realmente (por el modelo técnico) | Propiedad | Unidad real | Origen | ¿Relación con "attributable"? |
|---|---|---|---|---|---|
| `card_node_complete` / `render_node_complete` | `root_visibility_complete ∧ (nºFDs con ≥1 de 3 claves = nºFDs del nodo)` | A ∧ (E ∨ "pdev" ∨ "pasid") | **FD** | **OpenCode** (expresión y descripción ambas agente) | **supuesto, no establecido** |
| — su descriptor textual | dice *"complete **and attributable**"* mientras el baseline computaba **solo A** | — | — | OpenCode | descripción **sin expresión** en el baseline |
| `card_clients` / `render_clients` | nº de **FDs** que pasan el predicado, etiquetado como "clients" | — | **FD** (no `drm_file`) | OpenCode | — |
| `drm_fds_enumerated` | pooled, card+render juntos | A, evaluado pooled | FD pooled | OpenCode | — |
| `DRM_ATTRIBUTION_FIELDS` | tupla de 3 campos de **relaciones distintas** | — | — | OpenCode | **supuesto** |
| `clients_pasid_attributable` | lee debugfs, que **no** es la ruta de fdinfo | — | — | OpenCode | según el plan, **fila propia** |

**Clasificación de cada propiedad según su origen**:

- **Introducidas por el humano**: identidad PCI (§Ownership `:177`, `:32`); la exigencia de que la
  tabla sea completa ("complete", "FD visibility"); la negación de `OWNERSHIP=FULL` desde evidencia
  parcial.
- **Introducidas por OpenCode**: las dos filas de nodo; la tupla de 3 campos; el predicado; los
  contadores `*_clients`; la fusión de completitud y atribución en una fila; el agrupamiento pooled.
- **Únicamente inferidas**: que "attributable" deba satisfacerse con `drm-client-id`; que `drm-pdev`
  deba participar; que `pasid` deba participar; que la atribución deba ser por nodo y no por cliente.

---

# FASE 8 · REQUISITO HUMANO

| Campo | Contenido |
|---|---|
| `HUMAN_TEXT` | `AGENTS.md:176-177` — *"`FULL` requires complete attributable evidence for the RX550's **card and render nodes**, identified by PCI identity rather than by node name"*. Revisión `54b3ea8`: *"...complete, attributable evidence for `card1`, `renderD129`"* |
| `EXPLICIT_OBJECT` | **card** y **render nodes**; el método de identificación (**PCI identity, not node name**); el adjetivo **complete**. Tres cosas, todas explícitas |
| `IMPLICIT_OBJECT` | **ninguno identificable con evidencia**: no hay unmarked noun al que "attributable" se adhiera |
| `UNSPECIFIED_OBJECT` | **el destinatario de "attributable"**. Es la única parte no determinada del enunciado |
| `AGENT_INTERPRETATION` | `drm-client-id` + `drm-pdev` + `pasid` (la tupla); la exigencia de que la fila de nodo la satisfaga |
| `TECHNICAL_MEANING` | **no aplicable todavía**: sin objeto, no hay significado técnico que computar |
| `CONFLICTS` | (i) el plan asignó la atribución a **otra fila** (fila 11) — C-3; (ii) la spec permite unicidad de `client-id` **por dispositivo**, lo que cambia qué campos bastan (N-1) |

`REQUIREMENT_SEMANTICS` = **`UNRESOLVED`**

**No se inventa una definición.** El texto contiene tres requisitos explícitos y determinables, y una
palabra cuyo objeto falta. El modelo técnico no puede cerrar lo que el texto no cierra.

---

# FASE 9 · RESULTADO

## `TECHNICAL_SEMANTIC_MODEL`
14 entidades (§FASE 1). `drm_file` es la unidad de cliente; `drm-client-id` su identificador por
construcción; `drm-pdev` un atributo del **dispositivo**, no del cliente; el PID un atributo
**mutable con excepción master**; `driver_priv` **opaco**. `ESTABLISHED`, con `VM`/`PASID` en
`SOURCE_INCOMPLETE`.

## `TECHNICAL_RELATIONS`
14 relaciones. Las cinco que sostienen cualquier atribución: `FD ↔ drm_file` **N:1**, `drm_file →
client_id` **1:1 inmutable**, `drm_file → minor` **N:1**, `minor → drm_device`, `drm_device → PCI`
condicional. `PASID → proceso` **condicional y episódica**. `ESTABLISHED`; R12 `SOURCE_INCOMPLETE`.

## `OBSERVABILITY_MODEL`
Cinco capas no colapsables. Una sola superficie directa por propiedad: `/proc` para A y D, sysfs
para B, el texto de fdinfo para E/G/H, y **ninguna** para C sin `client_id`. `drm-client-id` ausente
tiene **cinco causas distinguibles, dos de ellas indistinguibles desde el texto**.

## `EVIDENCE_MODEL`
Cadena obligatoria: `EXPOSED → READABLE → OBSERVED → PROVES → SATISFIES`. Cortar un eslabón
impide afirmar el siguiente. El analizador llega a `READABLE+OBSERVED` en E, y **no** llega a
`VALUE` ni `DISCRIMINATION`.

## `PROJECT_REQUIREMENT_MAPPING`
Seis artefactos mapeados a propiedades técnicas, **todos de origen OpenCode**. Ninguno tiene
antecedente humano en su semántica actual. El requisito humano explícito cubre solo A y B.

## `AMBIGUITIES`
`AM-1` el objeto de "attributable" · `AM-2` si la identidad PCI es *qualifier* o *destinatario* ·
`AM-3` si la unicidad de `client-id` es global o por dispositivo en la spec (N-1) · `AM-4` si el
pid de un master es el del apertor o el del usuario actual (N-3) · `AM-5` qué significa
`drm-shared` cuando el buffer lo comparten dos clientes distintos.

## `CONFLICTS`
`C-1` `drm-client-id` vs *client ID* de page fault · `C-2` tres sentidos de "client" ·
`C-3` plan vs implementación sobre dónde vive la atribución · `C-4` **nuevo**: la implementación
hace `client_id` global, la spec permite por dispositivo (N-1). Todos `CONFLICT_UNRESOLVED`.

## `UNKNOWN`
`VM`/`PASID` en el kernel · `driver_priv` para amdgpu · si el passthrough cambia la cardinalidad de
R6 · si un FD puede reabrir el mismo `drm_file` tras un fork de la FD table.

## `FALSIFIERS`
| Afirmación | Lo que la refuta |
|---|---|
| R4 `client_id` 1:1 `drm_file` | dos `drm_file` con el mismo `client_id` |
| R5 pid mutable | `drm_file_update_pid` resultara inoperante |
| R6 1 minor por `drm_file` | un `drm_file` accesible desde dos nodos |
| E la presencia prueba identidad | un caso donde dos `drm_file` tengan la misma clave |
| G/H por `drm_file` | una clave de esas familias definida por proceso en la spec |
| N-1 unicidad por dispositivo | una implementación que asigne `client_id` global **y** omita `drm-pdev` en un dispositivo PCI — sería spec-conformante solo con la lectura global |

## `OPEN_DECISIONS`
1. El objeto de "attributable" — **no decidible por el modelo técnico**; es texto humano.
2. Si la identidad PCI es cualificador de alcance o destinatario de la atribución.
3. Si el proyecto debe asumir unicidad global de `client_id` o tolerar el par `(pdev, client_id)`.
4. Si la PID de un master se trata como el del apertor o el del usuario actual.

## `NEXT_MINIMAL_STEP`
**No es técnico.** El modelo técnico está completo hasta donde las fuentes llegan. El paso mínimo es
una **frase** del autor del requisito que nombre el destinatario de "attributable" en la oración de
`AGENTS.md:176-177`. Sin ella, las cuatro capacidades de FASE 5 no tienen destino y las seis
propiedades no tienen veredicto.

**Ninguna solución técnica se propone en este documento.**
