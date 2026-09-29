# R1-NORMATIVE-REQUIREMENT-DECOMPOSITION-20260926

`DOCUMENT_KIND` = `NORMATIVE_DECOMPOSITION` · **READ_ONLY + DOCUMENTACIÓN**
`TECHNICAL_MODEL_STATUS` = `CLOSED` — **no modificado, no reabierto**
`HUMAN_MIXED_TERM` = `RETIRED / NO_INTERPRETAR`
`REQUIREMENT_INTENT_RECONSTRUCTION` = `NOT_ATTEMPTED`
`PROJECT_MAPPING` = `NOT_ATTEMPTED` (hasta que corresponda explícitamente)
`PASS_FAIL` = **NOT_DEFINED** · `ANY_ALL` = **NOT_DECIDED** · `AGGREGATE_PROPERTY` = **PROHIBITED**
Cero cambios en collector, tests, runner, `AGENTS.md`, sysfs, GPU/PM, storage. Sin sudo, systemctl,
C1, `--run`, runtime, benchmarks, tuning ni commits. Ningún documento histórico reescrito ni
borrado; la nomenclatura histórica se preserva.

Base técnica (no re-derivada): `R1-TECHNICAL-MODEL-CLOSURE-20260926.md` (`ee86a3a7…`),
`R1-SEMANTIC-DECOMPOSITION-20260926.md` (`0801b7d9…`), `R1-TECHNICAL-SEPARATION-TABLE-20260926.md`
(`116f011e…`), `R1-ACTORS-INVENTORY-20260926.md` (`2767c476…`). Kernel de referencia: linux v6.12.

Este documento **no** modifica el modelo técnico y **no** decide qué debe exigir el proyecto.
Descompone un texto humano defectuoso en preguntas técnicas independientes.

---

## 1 · PROBLEMA DEL REQUISITO ANTERIOR

Texto de origen (`PROJECT_DOCUMENT`, `AGENTS.md:176-181`):

> `FULL` requires **complete attributable evidence** for the RX550's card and render nodes,
> **identified by PCI identity rather than by node name**
> …
> If **FD visibility is incomplete**, **a permission is denied**, **root namespaces are not
> covered**, **a client is active** or **a writer is unresolved**, then `OWNERSHIP != FULL`

Defectos demostrables en ese texto, sin recourse a la intención:

| # | Defecto | Evidencia |
|---|---|---|
| D-1 | **Una propiedad donde hay varias**: «complete attributable evidence» funde cobertura, legibilidad, identidad, asociación y atribución en un único sustantivo | cinco fuentes distintas (`/proc`, sysfs, `fdinfo`, `fdinfo`, debugfs) y dominios que no se corresponden |
| D-2 | **`attributable` no tiene unidad declarada**: cuatro conceptos que lo componían tienen cuatro unidades diferentes (FD, dispositivo, vmid, bloque) | `R1-TECHNICAL-MODEL-CLOSURE` §2–§5 |
| D-3 | **`client` es ambiguo en el propio core**: al menos cinco entidades distintas lo nombran | `drm_file` · fila del fichero debugfs `clients` · `drm_master` · GPU page-fault `client-id` · archivo sobre minor `accel` (`drm_is_accel_client`, `drm_file.h:432`) |
| D-4 | **La cláusula de fallo no discriminaba estados**: «no observado», «denegado», «no cubierto» y «resuelto» se expresan igual, aunque la evidencia disponible las distingue | `AGENTS.md` §Absence: seis estados, ninguno colapsable |
| D-5 | **«evidence» sin portador declarado**: no dice de qué evidence, ni de qué universo, ni con qué cobertura | — |

## 2 · POR QUÉ `attributable` SE RETIRA

Se retira como **propiedad normativa** por tres razones independientes, ninguna basada en
reconstruir intención:

1. **No tiene unidad.** Un predicado necesita una unidad; «attributable» no la tiene. Sin unidad no
   hay veredicto posible, ni `PASS` ni `FAIL`.
2. **No tiene predicado.** «Atribuible a qué» no está escrito, y las cuatro cosas a las que podría
   atribuirse están demostradas como **entidades distintas**, no como cuatro atributos de una.
3. **Su definición por unión está prohibida.** Definirlo como `drm-client-id ∧ drm-pdev ∧ pasid ∧
   pid ∧ fd ∧ memoria ∧ engine ∧ vm` recrearía exactamente el defecto: una palabra que
   reensambla dominios heterogéneos y borra cuál de ellos falló.

**Retirar el término no elimina el requisito humano.** Deja el requisito sin formalización
válida, y ese estado se nombra: `REQUIREMENT_UNRESOLVED`. No se rellena con una interpretación
del agente.

**No se crea ninguna palabra equivalente.** Prohibido: `attributable`, `atribución completa`,
`cliente atribuible`, `evidencia atribuible`, `DRM_ATTRIBUTION_FIELDS`, o cualquier renombre de
`ATTRIBUTABLE`. El antónimo tampoco: `NOT_ATTRIBUTABLE` no es una propiedad.

## 3 · LAS CUATRO PREGUNTAS, MANTENIDAS SEPARADAS

Ninguna de las cuatro implica la siguiente. Se mantienen explícitas para toda propiedad y para
toda implementación futura:

```
1. EXPOSED_BY_SYSTEM      ->  ¿el sistema expone el dato?
2. READABLE_BY_ANALYZER   ->  ¿nuestro analizador pudo leerlo?
3. PROVES_PROPERTY        ->  ¿el dato demuestra la propiedad?
4. SATISFIES_REQUIREMENT  ->  ¿la propiedad satisface el requisito?
```

| Tabla deconversion | Prohibido |
|---|---|
| expuesto | ⇒ leído |
| leído | ⇒ demuestra la propiedad |
| demuestra la propiedad | ⇒ satisface el requisito |
| `NOT_OBSERVED` | ⇒ objeto ausente |
| ausente | ⇒ `FAIL` (solo si el requisito **exige** que el atributo exista o sea demostrable) |
| denegado | ⇒ ausente |
| `OBSERVED` | ⇒ `PROVEN` |

`SATISFIES_REQUIREMENT` **no** se responde en esta etapa: `PROJECT_MAPPING = NOT_ATTEMPTED`.

## 4 · TABLA DE PROPIEDADES INDEPENDIENTES

Registro **normativo** (`N-n`), distinto del registro técnico (`P-n`/`S-n`) y del registro de
actores. El mapeo columna «REGISTRO_TÉCNICO» es una **referencia** a la semántica ya establecida;
**no** es una obligación de proyecto.

### N-1 · `NODE_COMPLETENESS`

- `PROPERTY`: `NODE_COMPLETENESS`

- `QUESTION`: ¿está completa la cobertura de FD/nodos DRM relevantes **según el universo definido**?
- `TECHNICAL_UNIT`: descriptor / proceso (cobertura), **no** cliente, **no** `drm-client-id`
- `SOURCE`: los cuatro términos de visibilidad del universo de FDs por nodo
- `WHAT_IT_ESTABLISHES`: si el universo de referencia quedó **recorrido**; y si no, **dónde** dejó de recorrerse
- `WHAT_IT_DOES_NOT_ESTABLISH`: identidad de cliente · asociación con proceso · actividad GPU · que el cliente esté inactivo · `complete` como atributo global
- `OBSERVABILITY_LIMITS`: depende del privilegio y del namespace; cobertura parcial no es cobertura completa. No cubre el tipo de minor `ACCEL` (`drm_file.h:65`), que la enumeración card/render no incluye
- `VALID_STATES`: `ESTABLISHED` · `PARTIAL` · `NOT_OBSERVED` · `ACCESS_DENIED` · `INDETERMINATE`
- `FALSIFIER`: el mismo universo y privilegio con las cuatro condiciones satisfechas y una fila de FDs ausente
- `PROVENANCE`: `HUMAN_REQUIREMENT` («complete», «FD visibility is incomplete»)

### N-2 · `NODE_DEVICE_IDENTITY`

- `PROPERTY`: `NODE_DEVICE_IDENTITY`

- `QUESTION`: ¿puede identificarse técnicamente el nodo DRM observado con el dispositivo PCI esperado?
- `TECHNICAL_UNIT`: **un dispositivo** (nodo). `drm-pdev` es su **dirección PCI**, no su identidad de cliente
- `SOURCE`: `drm-pdev` (`drm_file.c:948-950`, solo si `dev_is_pci`); `EXTERNAL_SPEC` `:59-62`; sysfs + `minor->dev`
- `WHAT_IT_ESTABLISHES`: que el nodo corresponde al BDF esperado
- `WHAT_IT_DOES_NOT_ESTABLISH`: identidad de cliente · número de clientes · que exista un `drm_file` asociado · quién lo abrió
- `OBSERVABILITY_LIMITS`: `drm-pdev` **no** existe para dispositivos no-PCI; no transporta vendor/device/class; la **unicidad** de la dirección no implica unicidad de nada más
- `VALID_STATES`: `ESTABLISHED` · `PARTIAL` (BDF sin vendor/device/class) · `NOT_EXPOSED` (dispositivo no-PCI) · `INDETERMINATE`
- `FALSIFIER`: `drm-pdev` emitiendo algo que no sea `domain:bus:slot.func`
- `PROVENANCE`: `HUMAN_REQUIREMENT` («identified by PCI identity rather than by node name»)

### N-3 · `FD_PROCESS_ASSOCIATION`

- `PROPERTY`: `FD_PROCESS_ASSOCIATION`

- `QUESTION`: ¿qué proceso posee/expone el FD observado?
- `TECHNICAL_UNIT`: **FD** (la **tenencia** del descriptor)
- `SOURCE`: `/proc/<pid>/fd/<n>` y la ruta `/proc`
- `WHAT_IT_ESTABLISHES`: qué proceso **poseía** ese descriptor en el instante de la observación
- `WHAT_IT_DOES_NOT_ESTABLISH`: que ese proceso sea el *cliente* · que sea un `struct drm_file` · que posea FD de otro nodo · la **otra** dirección (`drm_file` → proceso que lo **usa**), que **no** está entre N-1…N-10: existe solo en el registro técnico como S-2 `DRM_FILE_PROCESS_ASSOCIATION` (`drm_file.h:271-278`, `drm_debugfs.c:98-103`). Si el proyecto la necesita como requisito, debe descomponerse como propiedad propia; **no** es esta
- `OBSERVABILITY_LIMITS`: re-evaluable; no es una identidad estable. `NOT_OBSERVED` ≠ el proceso no tenía el FD
- `VALID_STATES`: `ESTABLISHED` · `NOT_OBSERVED` (sweep no lo alcanzó) · `ACCESS_DENIED` · `INDETERMINATE`
- `FALSIFIER`: una ruta `/proc/<pid>/fd/<n>` resuelta a un nodo distinto del registrado
- `PROVENANCE`: `HUMAN_REQUIREMENT` (implícito: «FD visibility», «root namespaces are not covered»)

### N-4 · `DRM_FILE_IDENTITY`

- `PROPERTY`: `DRM_FILE_IDENTITY`

- `QUESTION`: ¿puede relacionarse el FD observado con el `struct drm_file` correspondiente?
- `TECHNICAL_UNIT`: **una apertura DRM** (`struct drm_file`)
- `SOURCE`: `/proc/<pid>/fdinfo/<n>` (carrier fdinfo, `drm_file.c:936-950`); el recurso **núcleo** `debugfs/dri/<minor>/clients` (`drm_debugfs.c:73-113`, `:143`)
- `WHAT_IT_ESTABLISHES`: **cardinalidades exactas**: `FD → struct file` es **N:1**; `struct file → drm_file` es **1:1**; varios FD pueden referenciar **la misma** apertura por `dup()`/`fork()`
- `WHAT_IT_DOES_NOT_ESTABLISH`: que FD y `drm_file` sean sinónimos · el **valor** del identificador (eso es N-5) · que exista un PASID · que el proceso sea el cliente · que la actividad del proceso sea actividad GPU
- `OBSERVABILITY_LIMITS`: fdinfo **no** expone la identidad del `drm_file`; el carrier núcleo existe pero **no** fue preservado por el proyecto. `dup()`/`fork()` rompen toda 1:1 FD↔apertura
- `VALID_STATES`: `ESTABLISHED` · `PARTIAL` (fdinfo legible sin la clave) · `NOT_EXPOSED` · `ACCESS_DENIED` · `INDETERMINATE`
- `FALSIFIER`: dos FDs del mismo `drm_file` con identificadores distintos; o un `struct file` con dos `drm_file`
- `PROVENANCE`: `HUMAN_REQUIREMENT_VIA_AMBIGUOUS_TOKEN` (la palabra `client` del texto); resolución técnica de `TECHNICAL_MODEL`

### N-5 · `DRM_CLIENT_IDENTITY`

- `PROPERTY`: `DRM_CLIENT_IDENTITY`

- `QUESTION`: ¿se dispone del `drm-client-id` y bajo qué condiciones puede usarse para distinguir aperturas DRM?
- `TECHNICAL_UNIT`: **un `drm_file`**
- `SOURCE`: `drm_file.c:942-943` (emisión); `drm_file.c:132,142` (asignación, una sola escritura); `EXTERNAL_SPEC` `:64-72`
- `WHAT_IT_ESTABLISHES`: el **valor** del identificador, y que es 1:1 con `struct drm_file` en la implementación del core
- `WHAT_IT_DOES_NOT_ESTABLISH`: que sea PID · FD · proceso · `drm_master` · PASID · GPU page-fault `client-id` · el **número** de clientes · persistencia
- `OBSERVABILITY_LIMITS`: **disponibilidad** y **unicidad** son cuestiones distintas y se responden por separado. Unicidad declarada por la spec: **global o por dispositivo** (`C-4` `CONFLICT_UNRESOLVED`); la implementación del core usa un contador **de ámbito de módulo**, luego el valor es único dentro de la vida del módulo `drm` cargado. El proyecto **no preservó ningún valor**: `VALUE = NOT_AVAILABLE`
- `VALID_STATES`: `ESTABLISHED` (valor leído) · `PARTIAL` (presencia sin valor) · `NOT_EXPOSED` · `NOT_OBSERVED` · `ACCESS_DENIED` · `INDETERMINATE`
- `FALSIFIER`: dos `drm_file` con el mismo `drm-client-id`; o una segunda escritura a `client_id` en el core
- `PROVENANCE`: `HUMAN_REQUIREMENT_VIA_AMBIGUOUS_TOKEN` (la palabra `client`); semántica de `TECHNICAL_MODEL`

### N-6 · `PASID_ASSOCIATION`

- `PROPERTY`: `PASID_ASSOCIATION`

- `QUESTION`: ¿qué relación técnica con VM/PASID/proceso puede establecerse?
- `TECHNICAL_UNIT`: **vmid**
- `SOURCE`: `SOURCE_INCOMPLETE` — 0 ocurrencias de `pasid` en `drm-usage-stats.rst`; 0 en el core v6.12; convención de driver
- `WHAT_IT_ESTABLISHES`: nada en este host
- `WHAT_IT_DOES_NOT_ESTABLISH`: que PASID sea `drm-client-id` · que sea PID · que sea FD · **identidad permanente** del proceso · una relación con `drm_file`
- `OBSERVABILITY_LIMITS`: la relación VM↔PASID↔proceso es **episódica**: solo durante un page fault y con el proceso activo. `SOURCE_INCOMPLETE` **no** es ausencia y **no** es `FAIL`
- `VALID_STATES`: `NOT_ESTABLISHED_SOURCE_INCOMPLETE` · `INDETERMINATE` (solo estos dos son alcanzables hoy)
- `FALSIFIER`: `pasid` impreso junto a un PID sin fault concurrente
- `PROVENANCE`: **`AGENT_FORMALIZATION`** — el texto humano **no menciona PASID**. Fuera del requisito humano hasta decisión normativa posterior

### N-7 · `MEMORY_ASSOCIATION`

- `PROPERTY`: `MEMORY_ASSOCIATION`

- `QUESTION`: ¿qué estadísticas de memoria están asociadas al `drm_file` observado?
- `TECHNICAL_UNIT`: agregado **por `drm_file` y región**
- `SOURCE`: `drm_print_memory_stats` (`drm_file.c:828-840`); `EXTERNAL_SPEC` `:140-175` (clave base `drm-memory-<region>`, más `drm-shared-`, `drm-total-`, `drm-resident-`, `drm-purgeable-`, `drm-active-`)
- `WHAT_IT_ESTABLISHES`: consumo agregado de ese `drm_file` por región
- `WHAT_IT_DOES_NOT_ESTABLISH`: inventario de objetos · buffers del proceso · que `=0` pruebe no-uso · identidad de cliente
- `OBSERVABILITY_LIMITS`: **por driver**; el core no la produce por sí solo. `NOT_OBSERVED` en este host
- `VALID_STATES`: `ESTABLISHED` · `NOT_EXPOSED` (driver no la emite) · `NOT_OBSERVED` · `INDETERMINATE`
- `FALSIFIER`: una clave de memoria indexada por proceso en la spec; o `=0` con evidencia de uso del mismo `drm_file`
- `PROVENANCE`: **`AGENT_FORMALIZATION`** — el texto humano **no menciona memoria**

### N-8 · `ENGINE_ACTIVITY`

- `PROPERTY`: `ENGINE_ACTIVITY`

- `QUESTION`: ¿qué actividad de engine está asociada al cliente DRM según fdinfo?
- `TECHNICAL_UNIT`: `drm_file` × engine (ns acumuladas)
- `SOURCE`: `EXTERNAL_SPEC` `:79-137` (`drm-engine-<keystr>`; `:86` *«belonging to this client»*; `:88-89` **no monótona**)
- `WHAT_IT_ESTABLISHES`: tiempo que el engine pasó ocupado ejecutando trabajo **de ese `drm_file`**
- `WHAT_IT_DOES_NOT_ESTABLISH`: actividad **instantánea** · identidad de proceso · que `engine=0` signifique «no utiliza GPU» · inventario
- `OBSERVABILITY_LIMITS`: **por driver**; no monótona → ante un retroceso hay que retener el máximo. `NOT_OBSERVED` en este host
- `VALID_STATES`: `ESTABLISHED` · `NOT_EXPOSED` · `NOT_OBSERVED` · `INDETERMINATE`
- `FALSIFIER`: `drm-engine-*` indexada por proceso en la spec, o declarada monótona
- `PROVENANCE`: **`AGENT_FORMALIZATION`** — el texto humano **no menciona engine**

### N-9 · `DRM_MASTER_RELATION`

- `PROPERTY`: `DRM_MASTER_RELATION`

- `QUESTION`: ¿qué relación de master existe?
- `TECHNICAL_UNIT`: **un `drm_master`**
- `SOURCE`: `drm_lease.h`; `drm_lease.c`; `drm_auth.c:81` (`drm_is_current_master`); `drm_debugfs.c:92-105` (columna `master` de la fila, por `drm_file`)
- `WHAT_IT_ESTABLISHES`: qué `drm_file` posee el master de un nodo primario, y si es el master **actual**
- `WHAT_IT_DOES_NOT_ESTABLISH`: identidad de cliente · identidad de proceso · permanencia (**transferible** por leasing)
- `OBSERVABILITY_LIMITS`: por ioctl, **no** por fdinfo. `NOT_OBSERVED` en este host
- `VALID_STATES`: `ESTABLISHED` · `NOT_APPLICABLE` (nodo no primario) · `NOT_OBSERVED` · `INDETERMINATE`
- `FALSIFIER`: un master transferido sin `lessor`; o una columna `master` que no dependa de `drm_is_current_master`
- `PROVENANCE`: **`AGENT_FORMALIZATION`** — el texto humano **no menciona master**

### N-10 · `GEM_OBJECT_RELATION`

- `PROPERTY`: `GEM_OBJECT_RELATION`

- `QUESTION`: ¿qué relación puede establecerse entre el `drm_file` observado y los objetos GEM?
- `TECHNICAL_UNIT`: **un `drm_gem_object`**; la relación `drm_file → GEM` es **1:N** (`file->object_idr`)
- `SOURCE`: `drm_gem.h`; `drm_file.object_idr` = `drm_file.h:299-303` (doc) y `:304` (campo `struct idr`), protegido por `table_lock` (`:306`); el idr **mapea handles de objeto `mm` a punteros de objeto** (`drm_file.h:302`)
- `WHAT_IT_ESTABLISHES`: que los handles de objeto de ese `drm_file` alcanzan objetos GEM vía `object_idr`
- `WHAT_IT_DOES_NOT_ESTABLISH`: que el GEM sea el proceso · el cliente · el FD · una identidad de cualquiera de ellos
- `OBSERVABILITY_LIMITS`: exposición individual `SOURCE_INCOMPLETE`; `object_idr` no es observable desde el espacio de usuario en las fuentes leídas. `NOT_OBSERVED` en este host
- `VALID_STATES`: `NOT_ESTABLISHED` · `NOT_EXPOSED` · `NOT_OBSERVED` · `INDETERMINATE`
- `FALSIFIER`: una fuente que haga del GEM una identidad de proceso; o `object_idr` públicamente iterable
- `PROVENANCE`: **`AGENT_FORMALIZATION`** — el texto humano **no menciona GEM**

## 5 · PROVENIENCIA DE CADA PROPIEDAD

| | Propiedad | Procedencia | Antecedente humano literal | ¿Pertenece al requisito humano? |
|---|---|---|---|---|
| N-1 | `NODE_COMPLETENESS` | `HUMAN_REQUIREMENT` | «complete», «FD visibility is incomplete» | **SÍ** |
| N-2 | `NODE_DEVICE_IDENTITY` | `HUMAN_REQUIREMENT` | «identified by PCI identity rather than by node name» | **SÍ** |
| N-3 | `FD_PROCESS_ASSOCIATION` | `HUMAN_REQUIREMENT` (parcial) | «FD visibility», «root namespaces are not covered» | **SÍ**, derivación parcial |
| N-4 | `DRM_FILE_IDENTITY` | `HUMAN_REQUIREMENT_VIA_AMBIGUOUS_TOKEN` | la palabra «client», **retirada como ambigua**; resolución de `TECHNICAL_MODEL` | **NO por su cuenta**: depende de una decisión normativa posterior |
| N-5 | `DRM_CLIENT_IDENTITY` | `HUMAN_REQUIREMENT_VIA_AMBIGUOUS_TOKEN` | ídem | **NO por su cuenta** |
| N-6 | `PASID_ASSOCIATION` | **`AGENT_FORMALIZATION`** | **ninguno** — el texto no menciona PASID | **NO** |
| N-7 | `MEMORY_ASSOCIATION` | **`AGENT_FORMALIZATION`** | **ninguno** | **NO** |
| N-8 | `ENGINE_ACTIVITY` | **`AGENT_FORMALIZATION`** | **ninguno** | **NO** |
| N-9 | `DRM_MASTER_RELATION` | **`AGENT_FORMALIZATION`** | **ninguno** | **NO** |
| N-10 | `GEM_OBJECT_RELATION` | **`AGENT_FORMALIZATION`** | **ninguno** | **NO** |

**5 de 10** tienen antecedente humano directo o parcial; **5 de 10** son `AGENT_FORMALIZATION` pura y
**quedan fuera del requisito humano** hasta una decisión normativa posterior. No se inventa
ninguna obligación para ellas. `TECHNICAL_MODEL` es la fuente de la **semántica** de las 10, no de
su **exigencia**: una propiedad puede estar perfectamente definida y no ser requisito de nada.

N-4 y N-5 llevan un matiz que no debe ocultarse: su único puente con el texto humano es una palabra
que este documento **retira**. No son un requisito humano restaurado bajo otro nombre; son la
descomposición técnica de un término que se declaró ambiguo. Que eso baste para el proyecto es una
decisión que **no** se toma aquí.

## 6 · PROPIEDAD TÉCNICA ≠ REQUISITO NORMATIVO

| | Propiedad técnica | Requisito normativo |
|---|---|---|
| **Qué es** | una pregunta sobre el sistema, con unidad, fuente y falsificador | una obligación que el proyecto se impone |
| **Quién la escribe** | el análisis técnico (`TECHNICAL_MODEL`) | el proyecto / su autor |
| **Ejemplo** | N-5: «¿hay `drm-client-id` y bajo qué condiciones?» | «`OWNERSHIP=FULL` **exige** N-5 = `ESTABLISHED`» |
| **Existe sin el proyecto** | **SÍ** | **NO** |
| **Puede quedar sin uso** | **SÍ** | no |
| `PROJECT_MAPPING` | — | **`NOT_ATTEMPTED`** |

Las 10 propiedades existen con independencia total de si el proyecto las exigiría. N-6…N-10 podrían
no ser exigidas nunca y seguirían siendo correctas.

## 7 · REGLAS ANTI-RECOMBINACIÓN (obligatorias para futuras implementaciones)

1. **Prohibido crear una propiedad agregada.** Ninguna propiedad nueva puede ser una unión, conjunción
   o un conjunto de las existentes. `DRM_ATTRIBUTION_FIELDS`, `ATTRIBUTABLE`, `NOT_ATTRIBUTABLE` y
   equivalentes: **PROHIBIDOS**, incluidos como nombre, constante, campo o test.
2. **Prohibido `any()`/`all()` sobre un conjunto genérico de «atribución».** Una decisión
   combinatoria solo puede existir **después** de que cada propiedad tenga definición normativa
   propia, y debe nombrar las propiedades concretas que combina, con su unidad.
3. **Cada propiedad conserva su unidad.** Nada que grounds en FD puede combinarse con nada que
   grounds en dispositivo, vmid, `drm_file` o bloque, sin declarar la conversión.
4. **Prohibido un nombre nuevo equivalente a `attributable`.** Si un nombre necesita justificarse
   por «lo que agrega», es un agregador y está prohibido.
5. **Prohibido colapsar las cuatro preguntas** (§3) en un único estado. Un artefacto que solo diga
   `leído` no puede sostener `PROVEN`, y `PROVEN` no puede sostener `SATISFIES_REQUIREMENT`.
6. **Prohibido convertir `NOT_OBSERVED` en ausencia**, y ausencia en `FAIL`, salvo que el requisito
   **exija** que el atributo exista o sea demostrable. Esa exigencia es una decisión normativa, no
   una inferencia técnica.
7. **Cada propiedad necesita antecedente humano explícito o la marca `AGENT_FORMALIZATION`.** Un
   nombre de agente no se presenta nunca como texto del humano.
8. **Un cambio de métrica, unidad, cobertura u observabilidad invalida el veredicto anterior** para
   la pregunta en curso; no se reutiliza.
9. **La identidad del dispositivo se declara por identidad PCI**, nunca por nombre de nodo; y
   `cardN` **no** es identidad entre hosts.
10. **Ninguna implementación puede reintroducir la conversión FD→cliente.** Varios FD pueden
    compartir una apertura DRM; el conteo de FDs no es el conteo de `drm_file`.

## 8 · FALSIFICADORES (consolidado)

| | Propiedad | Falsificador | `STATUS` |
|---|---|---|---|
| 1 | `NODE_COMPLETENESS` | mismo universo y privilegio con las 4 condiciones satisfechas y una fila de FDs ausente | `AVAILABLE` |
| 2 | `NODE_DEVICE_IDENTITY` | `drm-pdev` emitiendo algo que no sea `domain:bus:slot.func` | `AVAILABLE` |
| 3 | `FD_PROCESS_ASSOCIATION` | `/proc/<pid>/fd/<n>` resolviendo a otro nodo | `AVAILABLE` |
| 4 | `DRM_FILE_IDENTITY` | dos FDs del mismo `drm_file` con identificadores distintos; o un `struct file` con dos `drm_file` | `AVAILABLE` |
| 5 | `DRM_CLIENT_IDENTITY` | dos `drm_file` con el mismo `client_id`; o una segunda escritura a `client_id` | `AVAILABLE` |
| 5b | unicidad de `drm-client-id` | implementación por dispositivo con `client-id` repetido y `drm-pdev` presente → resolvería `C-4` | `AVAILABLE` |
| 5c | alcance de la unicidad | `client_id` repetido o reiniciado tras recargar el módulo `drm` | `AVAILABLE` |
| 6 | `PASID_ASSOCIATION` | `pasid` impreso junto a un PID sin fault concurrente | `AVAILABLE` |
| 7 | `MEMORY_ASSOCIATION` | clave de memoria indexada por proceso; o `=0` con uso probado del mismo `drm_file` | `AVAILABLE` |
| 8 | `ENGINE_ACTIVITY` | `drm-engine-*` por proceso, o declarada monótona | `AVAILABLE` |
| 8b | `engine=0` no prueba no-uso | spec que definiera `0` como «sin trabajo» | `AVAILABLE` |
| 9 | `DRM_MASTER_RELATION` | master transferido sin `lessor`; o columna `master` independiente de `drm_is_current_master` | `AVAILABLE` |
| 10 | `GEM_OBJECT_RELATION` | fuente que haga del GEM identidad de proceso; o `object_idr` públicamente iterable | `NOT_AVAILABLE` |
| — | las 4 preguntas separadas | un artefacto que reporte `leído` y lo use como `PROVEN` | `AVAILABLE` |

## 9 · QUEDA EXPLÍCITAMENTE SIN DECIDIR

| # | Cuestión | Por qué no se decide aquí | `CLASS` |
|---|---|---|---|
| U-1 | Cuáles de N-1…N-10 son **obligatorias** | decisión del proyecto, no del análisis | `REQUIREMENT_UNRESOLVED` |
| U-2 | Si alguna es **suficiente** por sí sola | depende de U-1 | `REQUIREMENT_UNRESOLVED` |
| U-3 | Cómo se combinan, si se combinan | requiere U-1 primero | `NOT_DECIDED` · `PASS_FAIL NOT_DEFINED` |
| U-4 | Qué veredicto corresponde a `OWNERSHIP` | requiere U-1 y la evidencia de cada propiedad | `NOT_DECIDED` |
| U-5 | Si N-4/N-5 entran, dado que su puente es un término retirado | decisión normativa | `REQUIREMENT_UNRESOLVED` |
| U-6 | Unicidad de `drm-client-id`: global o por dispositivo | la spec admite ambas; el core usa contador global de módulo | `CONFLICT_UNRESOLVED` (`C-4`) |
| U-7 | Sentidos de `client` (`C-1`, `C-2`) | falta fuente de amdgpu | `CONFLICT_UNRESOLVED` |
| U-8 | Relación VM/PASID/proceso, `driver_priv` amdgpu, page-fault `client-id` | fuentes de amdgpu inaccesibles | `SOURCE_INCOMPLETE` |
| U-9 | Si el tipo de minor `ACCEL` entra en el universo de nodos | la enumeración del proyecto es card/render; el modelo registra 4 tipos | `NOT_DECIDED` |
| U-10 | Qué hacer con la cláusula de fallo original («a client is active», «a writer is unresolved») | contiene el término retirado y una categoría no descompuesta | `REQUIREMENT_UNRESOLVED` |

**Ninguna de estas se convierte en `FAIL` ni en ausencia.** `SOURCE_INCOMPLETE` no es ausencia.

## 10 · ESTADO FINAL

```
TECHNICAL_MODEL                   = CLOSED   (no modificado, no reabierto)
HUMAN_MIXED_TERM                  = RETIRED / NO_INTERPRETAR
NORMATIVE_REQUIREMENT             = DECOMPOSED  (10 propiedades independientes, 0 agregadas)
REQUIREMENT_INTENT_RECONSTRUCTION = NOT_ATTEMPTED
PROJECT_MAPPING                   = NOT_ATTEMPTED
PASS_FAIL                         = NOT_DEFINED
ANY_ALL                           = NOT_DECIDED
AGGREGATE_PROPERTY                = PROHIBITED
NORMATIVE_PROPERTIES_FROM_HUMAN   = 5  (N-1, N-2, N-3, N-4*, N-5*)  *vía token retirado
NORMATIVE_AGENT_FORMALIZATIONS    = 5  (N-6..N-10, fuera del requisito humano)
HISTORICAL_DOCUMENTS_REWRITTEN    = 0
CODE_OR_TEST_OR_AGENTS_CHANGES    = NONE
```

**Lo que esta etapa hizo**: retiró el término humano defectuoso y dejó cada relación técnica con su
propio nombre, unidad, fuente, límite de observabilidad y falsificador.

**Lo que esta etapa NO hizo**: decidir qué exige el proyecto, elegir veredictos, combinar
propiedades, reconstruir la intención del humano, ni tocar el modelo técnico cerrado.

---

## 11 · `AUDIT` — N-1…N-10 contra el registro técnico

Auditado contra `R1-TECHNICAL-SEMANTIC-MODEL-20260926.md` (v1, `7ed820ef…`, **HISTORICAL**; sus
afirmaciones superadas no se rederivan) y contra el registro vigente `S-1…S-7` /
`P-1…P-17`. Nueve campos por propiedad: unidad, entidad, fuente, semántica, observabilidad,
mutabilidad, falsificador, procedencia, antecedente humano.

**3 defectos encontrados y corregidos en este documento:**

| # | Defecto | Tipo | Corrección |
|---|---|---|---|
| **D-1** | N-3 remitía a **«N-4b»**, una propiedad **inexistente** | referencia colgante | la dirección `drm_file` → proceso que lo usa **no** está entre N-1…N-10; apunta a S-2 y registra el hueco como **U-11** |
| **D-2** | N-10 citaba `object_idr` en `drm_file.h:287-293`, que es el bloque de **`lhead`** | `PROVENANCE_ERROR` | corregido a `drm_file.h:299-303` (doc) / `:304` (campo) / `:306` (`table_lock`); y la semántica ajustada: el idr mapea **handles de objeto `mm`** → punteros, no «handles del `drm_file`» |
| **D-3** | el nombre **`DRM_FILE_IDENTITY`** designa **dos preguntas distintas** en dos registros: N-4 (relación FD→`drm_file`) y S-1 (identidad del `drm_file` y su `client-id`) | `NAME_COLLISION` | el nombre normativo se conserva; se exige **prefijo de registro** (`N-4` vs `S-1`) en todo uso. Ver tabla abajo |

**D-3 · por qué importa**: un mismo nombre desnudo con dos preguntas y dos unidades es exactamente
la clase de defecto que este trabajo elimina. No se renombra la propiedad —el nombre normativo fue
fijado—; se prohíbe su uso sin calificar.

| | Registro | Pregunta | Unidad |
|---|---|---|---|
| `DRM_FILE_IDENTITY` | **N-4** (normativo) | ¿puede relacionarse el FD con el `struct drm_file`? | una apertura DRM (relación `FD → struct file → drm_file`, **N:1** por `dup()`/`fork()`) |
| `DRM_FILE_IDENTITY` | **S-1** (técnico) | ¿qué identidad tiene el `struct drm_file`? | un `drm_file` (su `drm-client-id`, **1:1**) |

Corolario ya vigente: N-4 trata la **cardinalidad**; N-5 trata el **valor**. No son la misma
pregunta.

**Sin defecto — verificado, no modificado:** `PROJECT_MAPPING = NOT_ATTEMPTED` intacto en 4 puntos ·
`any()`/`all()` aparece **1 sola vez**, como prohibición (`:277`) · `attributable` aparece **6 veces**,
todas como cita del texto retirado, diagnóstico o prohibición; **ninguna** como propiedad · ningún
`DRM_ATTRIBUTION_FIELDS` ni `ATTRIBUTABLE` en **ningún `.py`** (código limpio) · las 9
equivalencias prohibidas aparecen solo **negadas** (11 negaciones) · N-6…N-10 siguen
`AGENT_FORMALIZATION` con «¿Pertenece al requisito humano? **NO**» · N-4/N-5 siguen marcadas
`HUMAN_REQUIREMENT_VIA_AMBIGUOUS_TOKEN` con «**NO por su cuenta**» · N-1/N-2/N-3 no aparecen
mezcladas con `client-id`/PASID/memory/engine en ninguna dirección · las ocurrencias restantes de
`attributable` y `DRM_ATTRIBUTION_FIELDS` están **solo** en documentos `HISTORICAL`/`SUPERSEDED` o
citadas como retiradas, y se preservan.

**Fuera de alcance, detectado y NO corregido:** `R1-ATTRIBUTION-DECOMPOSITION-MODEL-20260926.md:259`
afirma `CURRENT` que `DRM_ATTRIBUTION_FIELDS` (`:1033`) alimenta `any()` (`:2783`). Esa afirmación
está **desactualizada**: el campo fue eliminado del collector. Documento fuera del alcance de esta
auditoría; no se edita aquí. `STALE_CLAIM_OUT_OF_SCOPE`.

**U-11 (nuevo, sin resolver)**: la dirección `drm_file` → proceso que lo usa existe en el registro
técnico (S-2) y **no** tiene propiedad normativa propia. No se añade N-11: crearla sería una
decisión normativa. `REQUIREMENT_UNRESOLVED`.
